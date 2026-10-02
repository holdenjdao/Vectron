// Landing page behaviour: tuck the announcement bar and dock the nav once the
// page scrolls, show the back-to-top button, and fade sections in.

document.documentElement.classList.add("js");

const announce = document.querySelector(".announce");
const nav = document.querySelector(".nav");
const toTop = document.querySelector(".to-top");

const onScroll = () => {
  const y = window.scrollY;
  announce?.classList.toggle("is-tucked", y > 40);
  nav?.classList.toggle("is-scrolled", y > 40);
  toTop?.classList.toggle("is-visible", y > window.innerHeight * 0.8);
};
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

toTop?.addEventListener("click", () => window.scrollTo({ top: 0 }));

const reveals = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-in");
        observer.unobserve(entry.target);
      }
    },
    { rootMargin: "0px 0px -10% 0px" },
  );
  reveals.forEach((el) => observer.observe(el));
} else {
  reveals.forEach((el) => el.classList.add("is-in"));
}
