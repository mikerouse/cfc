import { useState, useEffect } from 'react';

/**
 * Hook to detect device type and screen size
 * Following mobile-first principles from CLAUDE.md
 */
export const useDeviceType = () => {
  const [deviceInfo, setDeviceInfo] = useState({
    isMobile: false,
    isTablet: false,
    isDesktop: false,
    width: 0,
    height: 0
  });

  useEffect(() => {
    const updateDeviceInfo = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      // Breakpoints from CLAUDE.md
      const isMobile = width < 640;   // xs (default): 0px - 639px
      const isTablet = width >= 640 && width < 1024;  // sm + md: 640px - 1023px
      const isDesktop = width >= 1024; // lg + xl: 1024px+
      
      setDeviceInfo({
        isMobile,
        isTablet,
        isDesktop,
        width,
        height
      });
    };

    // Initial check
    updateDeviceInfo();

    // Listen for resize events
    window.addEventListener('resize', updateDeviceInfo);
    
    // Listen for orientation changes on mobile
    window.addEventListener('orientationchange', () => {
      // Delay to allow for orientation change to complete
      setTimeout(updateDeviceInfo, 100);
    });

    return () => {
      window.removeEventListener('resize', updateDeviceInfo);
      window.removeEventListener('orientationchange', updateDeviceInfo);
    };
  }, []);

  return deviceInfo;
};