"""
API endpoints for the new React-based comparison basket system
"""
import json
import csv
from io import StringIO
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from council_finance.models import Council, DataField, FinancialYear, CouncilCharacteristic, FinancialFigure
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def get_basket_data(request):
	"""
	Get current comparison basket data with council details
	"""
	try:
		basket_slugs = request.session.get('compare_basket', [])
		councils = Council.objects.filter(slug__in=basket_slugs).select_related(
			'council_type', 'council_nation'
		)
		
		# Preserve order from session
		council_dict = {c.slug: c for c in councils}
		ordered_councils = [council_dict[slug] for slug in basket_slugs if slug in council_dict]
		
		council_data = []
		for council in ordered_councils:
			council_data.append({
				'slug': council.slug,
				'name': council.name,
				'council_type': {
					'name': council.council_type.name if council.council_type else None
				},
				'council_nation': {
					'name': council.council_nation.name if council.council_nation else None
				},
				'population': council.latest_population,
				'latest_year': getattr(council, 'latest_year_label', None),
			})
		
		return JsonResponse({
			'success': True,
			'councils': council_data,
			'count': len(council_data)
		})
		
	except Exception as e:
		logger.error(f"Error getting basket data: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': str(e)
		}, status=500)

@require_http_methods(["GET"])
def get_available_fields(request):
	"""
	Get available data fields for comparison with categories
	"""
	try:
		fields = DataField.objects.all().select_related('dataset_type').order_by('category', 'name')
		
		field_data = []
		for field in fields:
			field_data.append({
				'slug': field.slug,
				'name': field.name,
				'description': field.explanation,
				'category': field.category or 'other',
				'data_type': getattr(field, 'data_type', 'text'),
				'unit': getattr(field, 'unit', None),
				'content_type': field.dataset_type.model if field.dataset_type else None,
			})
		
		return JsonResponse({
			'success': True,
			'fields': field_data,
			'count': len(field_data)
		})
		
	except Exception as e:
		logger.error(f"Error getting available fields: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': str(e)
		}, status=500)

@require_http_methods(["GET"])
def get_available_years(request):
	"""
	Get available financial years for comparison
	"""
	try:
		years = FinancialYear.objects.all().order_by('-label')
		
		year_data = []
		for year in years:
			# Count how many councils have data for this year
			data_count = FinancialFigure.objects.filter(year=year).count()
			
			year_data.append({
				'id': year.id,
				'label': year.label,
				'start_date': year.start_date.isoformat() if year.start_date else None,
				'end_date': year.end_date.isoformat() if year.end_date else None,
				'data_count': data_count,
			})
		
		return JsonResponse({
			'success': True,
			'years': year_data,
			'count': len(year_data)
		})
		
	except Exception as e:
		logger.error(f"Error getting available years: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': str(e)
		}, status=500)

@require_POST
def get_comparison_data(request):
	"""
	Get comparison data for specified councils, fields, and years
	"""
	try:
		data = json.loads(request.body)
		council_slugs = data.get('councils', [])
		field_slugs = data.get('fields', [])
		year_labels = data.get('years', [])
		
		if not all([council_slugs, field_slugs, year_labels]):
			return JsonResponse({
				'success': False,
				'error': 'Missing required parameters: councils, fields, or years'
			}, status=400)
		
		# Get objects
		councils = Council.objects.filter(slug__in=council_slugs)
		fields = DataField.objects.filter(slug__in=field_slugs)
		years = FinancialYear.objects.filter(label__in=year_labels)
		
		# Build comparison data structure
		comparison_data = {}
		
		for council in councils:
			comparison_data[council.slug] = {}
			
			for field in fields:
				comparison_data[council.slug][field.slug] = {}
				
				for year in years:
					value_data = get_field_value_for_council_year(council, field, year)
					comparison_data[council.slug][field.slug][year.label] = value_data
		
		return JsonResponse({
			'success': True,
			'data': comparison_data,
			'metadata': {
				'councils': len(councils),
				'fields': len(fields),
				'years': len(years),
			}
		})
		
	except json.JSONDecodeError:
		return JsonResponse({
			'success': False,
			'error': 'Invalid JSON data'
		}, status=400)
	except Exception as e:
		logger.error(f"Error getting comparison data: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': str(e)
		}, status=500)

def get_field_value_for_council_year(council, field, year):
	"""
	Get the value of a specific field for a council in a specific year
	Returns a dictionary with value and per_capita information
	"""
	try:
		# Try to get the data based on field category and type
		# First try non-temporal data (characteristics)
		if field.category == 'characteristic' or field.slug in ['population', 'elected_members', 'council_type', 'council_nation']:
			try:
				characteristic = CouncilCharacteristic.objects.get(
					council=council,
					field=field
				)
				return {
					'value': characteristic.value,
					'per_capita': getattr(characteristic, 'per_capita_value', None)
				}
			except CouncilCharacteristic.DoesNotExist:
				pass
		
		# Try temporal financial data
		try:
			obj = FinancialFigure.objects.get(
				council=council,
				year=year,
				field=field
			)
			value = obj.value
			per_capita = None
			
			# Calculate per capita if we have population
			if value is not None and council.latest_population:
				try:
					per_capita = float(value) / float(council.latest_population)
				except (ValueError, ZeroDivisionError):
					pass
			
			return {
				'value': value,
				'per_capita': per_capita
			}
		except FinancialFigure.DoesNotExist:
			pass
		
		return {
			'value': None,
			'per_capita': None
		}
		
	except Exception as e:
		logger.error(f"Error getting field value for {council.slug}, {field.slug}, {year.label}: {str(e)}")
		return {
			'value': None,
			'per_capita': None
		}

@require_POST
def export_comparison_data(request):
	"""
	Export comparison data in CSV or JSON format
	"""
	try:
		data = json.loads(request.body)
		council_slugs = data.get('councils', [])
		field_slugs = data.get('fields', [])
		year_labels = data.get('years', [])
		export_format = data.get('format', 'csv').lower()
		
		if not all([council_slugs, field_slugs, year_labels]):
			return JsonResponse({
				'success': False,
				'error': 'Missing required parameters: councils, fields, or years'
			}, status=400)
		
		# Get objects
		councils = Council.objects.filter(slug__in=council_slugs).order_by('name')
		fields = DataField.objects.filter(slug__in=field_slugs)
		years = FinancialYear.objects.filter(label__in=year_labels).order_by('-label')
		
		# Build export data
		export_data = []
		
		# Add headers
		if export_format == 'csv':
			headers = ['Council', 'Council Type', 'Nation']
			for field in fields:
				for year in years:
					if len(years) > 1:
						headers.append(f"{field.name} ({year.label})")
						headers.append(f"{field.name} Per Capita ({year.label})")
					else:
						headers.append(field.name)
						headers.append(f"{field.name} Per Capita")
			
			export_data.append(headers)
		
		# Add council data
		for council in councils:
			if export_format == 'csv':
				row = [
					council.name,
					council.council_type.name if council.council_type else '',
					council.council_nation.name if council.council_nation else ''
				]
				
				for field in fields:
					for year in years:
						value_data = get_field_value_for_council_year(council, field, year)
						row.append(value_data.get('value', ''))
						row.append(value_data.get('per_capita', ''))
				
				export_data.append(row)
			
			else:  # JSON format
				council_data = {
					'council': {
						'slug': council.slug,
						'name': council.name,
						'type': council.council_type.name if council.council_type else None,
						'nation': council.council_nation.name if council.council_nation else None,
						'population': council.latest_population,
					},
					'data': {}
				}
				
				for field in fields:
					council_data['data'][field.slug] = {
						'field_name': field.name,
						'years': {}
					}
					
					for year in years:
						value_data = get_field_value_for_council_year(council, field, year)
						council_data['data'][field.slug]['years'][year.label] = value_data
				
				export_data.append(council_data)
		
		# Generate response
		if export_format == 'csv':
			output = StringIO()
			writer = csv.writer(output)
			writer.writerows(export_data)
			
			response = HttpResponse(output.getvalue(), content_type='text/csv')
			response['Content-Disposition'] = 'attachment; filename="council_comparison.csv"'
			return response
		
		else:  # JSON format
			response = HttpResponse(
				json.dumps(export_data, indent=2),
				content_type='application/json'
			)
			response['Content-Disposition'] = 'attachment; filename="council_comparison.json"'
			return response
		
	except json.JSONDecodeError:
		return JsonResponse({
			'success': False,
			'error': 'Invalid JSON data'
		}, status=400)
	except Exception as e:
		logger.error(f"Error exporting comparison data: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': str(e)
		}, status=500)

class ComparisonBasketView(View):
	"""
	Main view for the comparison basket page
	"""
	def get(self, request):
		"""
		Render the comparison basket page with initial data
		"""
		from django.shortcuts import render
		
		# Get basket councils
		basket_slugs = request.session.get('compare_basket', [])
		councils = Council.objects.filter(slug__in=basket_slugs).select_related(
			'council_type', 'council_nation'
		)
		
		# Preserve order
		council_dict = {c.slug: c for c in councils}
		ordered_councils = [council_dict[slug] for slug in basket_slugs if slug in council_dict]
		
		# Get available fields and years
		available_fields = DataField.objects.all().order_by('category', 'name')
		available_years = FinancialYear.objects.all().order_by('-label')
		
		# Prepare initial data for React
		initial_data = {
			'councils': [
				{
					'slug': council.slug,
					'name': council.name,
					'council_type': {
						'name': council.council_type.name if council.council_type else None
					},
					'council_nation': {
						'name': council.council_nation.name if council.council_nation else None
					},
					'population': council.latest_population,
					'latest_year': getattr(council, 'latest_year_label', None),
				}
				for council in ordered_councils
			],
			'availableFields': [
				{
					'slug': field.slug,
					'name': field.name,
					'description': field.explanation,
					'category': field.category or 'other',
					'data_type': getattr(field, 'data_type', 'text'),
					'unit': getattr(field, 'unit', None),
				}
				for field in available_fields
			],
			'availableYears': [
				{
					'id': year.id,
					'label': year.label,
				}
				for year in available_years
			],
			'selectedFields': [],
			'selectedYears': [
				{
					'id': available_years[0].id,
					'label': available_years[0].label,
				}
			] if available_years else [],  # Default to latest year
		}
		
		context = {
			'page_title': 'Council Comparison Basket',
			'initial_data_json': json.dumps(initial_data),
			'council_count': len(ordered_councils),
		}
		
		return render(request, 'council_finance/comparison_basket_react.html', context)