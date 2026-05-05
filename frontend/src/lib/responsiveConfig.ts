/**
 * Responsive utility file for Ovulite Mobile-First Design
 * Breakpoints: 320px (xs), 640px (sm), 768px (md), 1024px (lg), 1280px (xl), 1536px (2xl)
 */

export const responsiveConfig = {
  breakpoints: {
    xs: 320,
    sm: 640,
    md: 768,
    lg: 1024,
    xl: 1280,
    '2xl': 1536,
  },
  
  // Responsive font sizes
  fontSize: {
    // Title/Hero
    title: {
      xs: '24px',  // Mobile
      sm: '28px',  // Tablet small
      md: '32px',  // Tablet
      lg: '40px',  // Desktop
      xl: '48px',  // Large desktop
    },
    
    // Heading XL
    headingXl: {
      xs: '20px',
      sm: '24px',
      md: '28px',
      lg: '32px',
      xl: '40px',
    },
    
    // Heading Large
    headingLg: {
      xs: '18px',
      sm: '20px',
      md: '24px',
      lg: '28px',
      xl: '32px',
    },
    
    // Heading Medium
    headingMd: {
      xs: '16px',
      sm: '18px',
      md: '20px',
      lg: '24px',
      xl: '28px',
    },
    
    // Base
    base: {
      xs: '14px',
      sm: '14px',
      md: '16px',
      lg: '16px',
      xl: '16px',
    },
    
    // Small
    small: {
      xs: '12px',
      sm: '12px',
      md: '14px',
      lg: '14px',
      xl: '14px',
    },
  },

  // Responsive spacing
  spacing: {
    page: {
      xs: '12px',
      sm: '16px',
      md: '24px',
      lg: '32px',
      xl: '40px',
    },
    section: {
      xs: '16px',
      sm: '20px',
      md: '24px',
      lg: '32px',
      xl: '40px',
    },
    gap: {
      xs: '12px',
      sm: '16px',
      md: '20px',
      lg: '24px',
      xl: '32px',
    },
  },

  // Responsive grid columns
  grid: {
    kpi: {
      xs: '1',    // 1 column on mobile
      sm: '2',    // 2 columns on tablet
      md: '2',    // 2 columns on tablet
      lg: 'auto-fit, minmax(250px, 1fr)',
      xl: 'auto-fit, minmax(300px, 1fr)',
    },
    card: {
      xs: '1',
      sm: '1',
      md: '2',
      lg: '3',
      xl: '4',
    },
    panel: {
      xs: '1',
      sm: '1',
      md: '2',
      lg: '2',
      xl: '2',
    },
  },

  // Container sizes
  container: {
    xs: '100%',
    sm: '540px',
    md: '720px',
    lg: '960px',
    xl: '1140px',
    '2xl': '1320px',
  },
};

// Tailwind-ready CSS variables
export const responsiveStyles = `
  :root {
    /* Mobile-first base sizes */
    --font-title: 24px;
    --font-heading-xl: 20px;
    --font-heading-lg: 18px;
    --font-heading-md: 16px;
    --font-base: 14px;
    --font-small: 12px;
    
    --spacing-page: 12px;
    --spacing-section: 16px;
    --spacing-gap: 12px;
  }

  /* Tablet (640px+) */
  @media (min-width: 640px) {
    :root {
      --font-title: 28px;
      --font-heading-xl: 24px;
      --font-heading-lg: 20px;
      --font-heading-md: 18px;
      --font-base: 14px;
      --font-small: 12px;
      
      --spacing-page: 16px;
      --spacing-section: 20px;
      --spacing-gap: 16px;
    }
  }

  /* Tablet (768px+) */
  @media (min-width: 768px) {
    :root {
      --font-title: 32px;
      --font-heading-xl: 28px;
      --font-heading-lg: 24px;
      --font-heading-md: 20px;
      --font-base: 16px;
      --font-small: 14px;
      
      --spacing-page: 24px;
      --spacing-section: 24px;
      --spacing-gap: 20px;
    }
  }

  /* Desktop (1024px+) */
  @media (min-width: 1024px) {
    :root {
      --font-title: 40px;
      --font-heading-xl: 32px;
      --font-heading-lg: 28px;
      --font-heading-md: 24px;
      --font-base: 16px;
      --font-small: 14px;
      
      --spacing-page: 32px;
      --spacing-section: 32px;
      --spacing-gap: 24px;
    }
  }

  /* Large Desktop (1280px+) */
  @media (min-width: 1280px) {
    :root {
      --font-title: 48px;
      --font-heading-xl: 40px;
      --font-heading-lg: 32px;
      --font-heading-md: 28px;
      --font-base: 16px;
      --font-small: 14px;
      
      --spacing-page: 40px;
      --spacing-section: 40px;
      --spacing-gap: 32px;
    }
  }
`;

// Media query helpers
export const media = {
  xs: '(min-width: 320px)',
  sm: '(min-width: 640px)',
  md: '(min-width: 768px)',
  lg: '(min-width: 1024px)',
  xl: '(min-width: 1280px)',
  '2xl': '(min-width: 1536px)',
  
  // Max queries for mobile-first
  maxXs: '(max-width: 639px)',
  maxSm: '(max-width: 767px)',
  maxMd: '(max-width: 1023px)',
  maxLg: '(max-width: 1279px)',
};

export default responsiveConfig;
