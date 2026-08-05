"use client";

import { useEffect, useState, type ReactNode } from "react";

import type { Slide } from "@/lib/showcase-content";

const AUTOPLAY_MS = 5000;

export function Carousel({ slides }: { slides: Slide[] }): ReactNode {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused || slides.length <= 1) return;
    const id = setInterval(
      () => setIndex((i) => (i + 1) % slides.length),
      AUTOPLAY_MS,
    );
    return () => clearInterval(id);
  }, [paused, slides.length]);

  function go(next: number): void {
    setIndex(((next % slides.length) + slides.length) % slides.length);
  }

  return (
    <div
      className="carousel"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <button
        className="car-arrow"
        onClick={() => go(index - 1)}
        aria-label="Oldingi"
      >
        ‹
      </button>

      <div className="car-viewport">
        <div
          className="car-track"
          style={{ transform: `translateX(-${index * 100}%)` }}
        >
          {slides.map((slide) => (
            <article className="car-slide" key={slide.tag}>
              <div className="car-icon">{slide.icon}</div>
              <span className="pill">{slide.tag}</span>
              <h3>{slide.title}</h3>
              <ul>
                {slide.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>

      <button
        className="car-arrow"
        onClick={() => go(index + 1)}
        aria-label="Keyingi"
      >
        ›
      </button>

      <div className="car-dots">
        {slides.map((slide, i) => (
          <button
            key={slide.tag}
            className={i === index ? "active" : ""}
            onClick={() => setIndex(i)}
            aria-label={`${i + 1}-slayd`}
          />
        ))}
      </div>
    </div>
  );
}
