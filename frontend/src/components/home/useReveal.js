import { useEffect } from 'react';

/**
 * Adds a gentle fade-and-rise as each `.hp-reveal` block enters the viewport.
 *
 * Deliberately restrained: one transition, once per element, and skipped
 * entirely when the visitor prefers reduced motion or the browser has no
 * IntersectionObserver — in both cases everything is simply shown.
 */
export function useReveal() {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll('.hp-reveal'));
    if (!nodes.length) return undefined;

    const reduced =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduced || typeof IntersectionObserver === 'undefined') {
      nodes.forEach((node) => node.classList.add('shown'));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('shown');
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
    );

    nodes.forEach((node, index) => {
      node.style.transitionDelay = `${Math.min(index % 4, 3) * 70}ms`;
      observer.observe(node);
    });

    // Anything already on screen at load should not wait for a scroll.
    const raf = window.requestAnimationFrame(() => {
      nodes.forEach((node) => {
        if (node.getBoundingClientRect().top < window.innerHeight) {
          node.classList.add('shown');
          observer.unobserve(node);
        }
      });
    });

    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, []);
}

export default useReveal;
