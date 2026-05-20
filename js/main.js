const faders = document.querySelectorAll(".fade-up");

if ("IntersectionObserver" in window) {
  const appearOnScroll = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("show");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.18 });

  faders.forEach((fader) => appearOnScroll.observe(fader));
} else {
  faders.forEach((fader) => fader.classList.add("show"));
}

const demoForm = document.getElementById("demo-form");
const formStatus = document.getElementById("form-status");

if (demoForm && formStatus) {
  demoForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(demoForm);
    const name = String(formData.get("name") || "").trim();
    const useCase = String(formData.get("use-case") || "").trim();

    formStatus.textContent = name && useCase
      ? `Demo preparada para ${name}: ${useCase}. Este flujo es local y no envía datos.`
      : "Completa los datos para preparar la demo.";
  });
}
