// Progressive enhancement only: every page works without this file.
// <select data-autosubmit> submits its form as soon as the value changes.
document.addEventListener("change", (event) => {
  const target = event.target;
  if (target instanceof HTMLSelectElement && target.dataset.autosubmit !== undefined) {
    target.form?.requestSubmit();
  }
});

// <form data-confirm="Question?"> asks before submitting. Without JS it just submits.
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (form instanceof HTMLFormElement && form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
  }
});
