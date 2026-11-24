// Progressive enhancement only: every page works without this file.
// <select data-autosubmit> submits its form as soon as the value changes.
document.addEventListener("change", (event) => {
  const target = event.target;
  if (target instanceof HTMLSelectElement && target.dataset.autosubmit !== undefined) {
    target.form?.requestSubmit();
  }
});
