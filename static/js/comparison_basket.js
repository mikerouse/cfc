function getCookie(name){const m=document.cookie.match('(^|;)\s*'+name+'\s*=\s*([^;]+)');return m?m.pop():'';}
function updateBasketCount(count){const span=document.getElementById('basket-count');if(span){span.textContent=count;span.classList.toggle('hidden',count===0);}}

// Attach handler for the compare button on council detail pages
document.addEventListener('DOMContentLoaded',()=>{
  const btn=document.getElementById('compare-btn');
  if(btn){
    btn.addEventListener('click',()=>{
      const slug=btn.dataset.slug;const csrftoken=getCookie('csrftoken');
      fetch(`/compare/add/${slug}/`,{method:'POST',headers:{'X-CSRFToken':csrftoken}})
        .then(r=>r.json())
        .then(d=>{updateBasketCount(d.count);btn.disabled=true;btn.textContent='Added';});
    });
  }
  document.querySelectorAll('.remove-compare').forEach(el=>{
    el.addEventListener('click',e=>{
      e.preventDefault();const slug=el.dataset.slug;const csrftoken=getCookie('csrftoken');
      fetch(`/compare/remove/${slug}/`,{method:'POST',headers:{'X-CSRFToken':csrftoken}})
        .then(()=>window.location.reload());
    });
  });
  const sel=document.getElementById('field-select');
  if(sel){
    sel.addEventListener('change',()=>{
      const slug=sel.value;if(!slug)return;
      fetch(`/compare/row/?field=${encodeURIComponent(slug)}`,{headers:{'X-Requested-With':'XMLHttpRequest'}})
        .then(r=>r.text())
        .then(html=>{document.getElementById('compare-rows').insertAdjacentHTML('beforeend',html);sel.selectedIndex=0;});
    });
  }
});
