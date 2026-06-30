import { useEffect, useRef, useState } from 'react';

export default function AnimatedNumber({ value, duration = 800, decimals = 0 }) {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef(null);
  const startRef = useRef(null);
  const fromRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    const to = Number(value) || 0;
    startRef.current = null;

    const step = (timestamp) => {
      if (!startRef.current) startRef.current = timestamp;
      const progress = Math.min((timestamp - startRef.current) / duration, 1);
      const eased = 1 - (1 - progress) ** 3;
      const current = from + (to - from) * eased;
      setDisplay(current);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        fromRef.current = to;
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameRef.current);
  }, [value, duration]);

  return <span>{display.toFixed(decimals)}</span>;
}
