/* Сайт публикаций — клиентские скрипты */
(function () {
  "use strict";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function getCookie(name) {
    var m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }

  // --- Модальные окна -------------------------------------------------------
  function openModal(id) {
    var m = document.getElementById(id);
    if (m) m.classList.add("open");
  }
  function closeModal(el) {
    var overlay = el.closest(".modal-overlay") || el;
    overlay.classList.remove("open");
  }
  window.openModal = openModal;

  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-modal-open]");
    if (opener) {
      e.preventDefault();
      openModal(opener.getAttribute("data-modal-open"));
      return;
    }
    if (e.target.closest("[data-modal-close]")) {
      e.preventDefault();
      closeModal(e.target.closest(".modal-overlay"));
      return;
    }
    if (e.target.classList.contains("modal-overlay")) {
      e.target.classList.remove("open");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") $all(".modal-overlay.open, .lightbox.open").forEach(function (m) { m.classList.remove("open"); });
  });

  // --- Лайтбокс для фото ----------------------------------------------------
  var lightbox = $("#lightbox");
  if (lightbox) {
    document.addEventListener("click", function (e) {
      var img = e.target.closest("[data-lightbox]");
      if (img) {
        $("#lightbox-img").src = img.getAttribute("data-lightbox") || img.src;
        lightbox.classList.add("open");
      }
    });
  }

  // --- Динамическая валидация регистрации -----------------------------------
  var reg = $("#register-form");
  if (reg) {
    var name = reg.querySelector("[name=display_name]");
    var email = reg.querySelector("[name=email]");
    var p1 = reg.querySelector("[name=password1]");
    var p2 = reg.querySelector("[name=password2]");
    var terms = reg.querySelector("[name=terms]");
    var submit = reg.querySelector("[type=submit]");

    var nameRe = /^[\p{L}\p{N}]{1,15}$/u;
    var emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    function asciiOk(s) { return /^[\x00-\x7F]*$/.test(s); }
    function passOk(s) { return s.length >= 6 && s.length <= 15 && asciiOk(s); }

    function refresh() {
      var pass1Valid = passOk(p1.value);
      // Подтверждение пароля недоступно, пока пароль не валиден.
      p2.disabled = !pass1Valid;
      var ok = nameRe.test(name.value.trim()) &&
        emailRe.test(email.value.trim()) && asciiOk(email.value) &&
        pass1Valid && p1.value === p2.value && terms.checked;
      submit.disabled = !ok;
      submit.classList.toggle("disabled", !ok);
    }
    [name, email, p1, p2].forEach(function (el) { el.addEventListener("input", refresh); });
    terms.addEventListener("change", refresh);
    refresh();
  }

  // --- Кнопка "Сохранить" при восстановлении/смене пароля -------------------
  $all("[data-require-filled]").forEach(function (form) {
    var fields = $all("input[type=password]", form);
    var submit = form.querySelector("[type=submit]");
    function refresh() {
      var allFilled = fields.every(function (f) { return f.value.trim().length > 0; });
      submit.disabled = !allFilled;
      submit.classList.toggle("disabled", !allFilled);
    }
    fields.forEach(function (f) { f.addEventListener("input", refresh); });
    refresh();
  });

  // --- Вход: активировать кнопку только при заполнении ----------------------
  $all("[data-enable-when-filled]").forEach(function (form) {
    var fields = $all(".form-control", form);
    var submit = form.querySelector("[type=submit]");
    function refresh() {
      var ok = fields.every(function (f) { return f.value.trim().length > 0; });
      submit.disabled = !ok;
      submit.classList.toggle("disabled", !ok);
    }
    fields.forEach(function (f) { f.addEventListener("input", refresh); });
    refresh();
  });

  // --- Добавление публикации: блокировка полей до выбора категории + превью --
  var addForm = $("#listing-form");
  if (addForm) {
    var catSel = addForm.querySelector("[name=category]");
    var dependent = $all("[data-needs-category]", addForm);
    function toggleDependent() {
      var chosen = catSel && catSel.value;
      dependent.forEach(function (el) {
        el.querySelectorAll("input, textarea, button, label").forEach(function (i) {
          if (i.matches("input,textarea,button")) i.disabled = !chosen;
        });
        el.style.opacity = chosen ? "1" : ".5";
      });
    }
    if (catSel) { catSel.addEventListener("change", toggleDependent); toggleDependent(); }
  }

  // --- Превью выбранных фото -------------------------------------------------
  $all("input[type=file][data-preview]").forEach(function (input) {
    var box = document.getElementById(input.getAttribute("data-preview"));
    input.addEventListener("change", function () {
      if (!box) return;
      box.innerHTML = "";
      Array.prototype.forEach.call(input.files, function (file) {
        if (!file.type.startsWith("image/")) return;
        var img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        var w = document.createElement("div");
        w.className = "pv";
        w.appendChild(img);
        box.appendChild(w);
      });
    });
  });

  // --- Избранное (AJAX) ------------------------------------------------------
  $all("[data-favorite-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCookie("csrftoken") },
      }).then(function (r) { return r.json(); }).then(function (data) {
        var btn = form.querySelector("button");
        btn.textContent = data.added ? "Убрать из избранного" : "Добавить в избранное";
        showToast(data.message);
      });
    });
  });

  // --- Жалоба (AJAX) ---------------------------------------------------------
  var complaintForm = $("#complaint-form");
  if (complaintForm) {
    complaintForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var ta = complaintForm.querySelector("textarea");
      var err = complaintForm.querySelector(".field-error");
      var fd = new FormData(complaintForm);
      fetch(complaintForm.action, {
        method: "POST",
        body: fd,
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCookie("csrftoken") },
      }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (!res.ok) { if (err) err.textContent = res.d.message || "Введите текст"; return; }
          if (err) err.textContent = "";
          ta.value = "";
          closeModal(complaintForm);
          showToast(res.d.message);
        });
    });
  }

  // --- Простые уведомления ---------------------------------------------------
  function showToast(text) {
    var t = document.createElement("div");
    t.className = "alert alert-success";
    t.style.position = "fixed";
    t.style.bottom = "20px";
    t.style.left = "50%";
    t.style.transform = "translateX(-50%)";
    t.style.zIndex = "2000";
    t.style.boxShadow = "0 4px 14px rgba(0,0,0,.18)";
    t.textContent = text;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
  }
  window.showToast = showToast;
})();
