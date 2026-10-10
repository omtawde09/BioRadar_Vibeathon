import React from 'react';
import { createRoot } from 'react-dom/client';
import { HomePage } from './HomePage';

declare global {
  interface Window {
    BioRadarHomeMounted?: boolean;
    mountBioRadarHome?: (container: HTMLElement, onNavigateView?: (viewId: string) => void) => void;
  }
}

export function mountHome(container: HTMLElement, onNavigateView?: (viewId: string) => void) {
  const root = createRoot(container);
  root.render(<HomePage onNavigateView={onNavigateView} />);
}

window.mountBioRadarHome = mountHome;

// Auto-mount if a home container is already in DOM on load
document.addEventListener('DOMContentLoaded', () => {
  const homeContainer = document.getElementById('view-home') || document.getElementById('home-root');
  if (homeContainer && !window.BioRadarHomeMounted) {
    window.BioRadarHomeMounted = true;
    mountHome(homeContainer, (viewId) => {
      if ((window as any).BioRadarUI && (window as any).BioRadarUI.showView) {
        (window as any).BioRadarUI.showView(viewId);
      } else {
        window.location.hash = `#${viewId}`;
      }
    });
  }
});
