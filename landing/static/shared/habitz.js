// ===== FLASH AUTO-DISMISS =====
(function() {
    document.querySelectorAll('.flash').forEach(function(flash) {
        setTimeout(function() {
            flash.style.transition = 'opacity 0.3s, transform 0.3s';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-8px)';
            setTimeout(function() { flash.remove(); }, 300);
        }, 3000);
    });
})();

// ===== APP SWITCHER =====
(function() {
    var btn = document.getElementById("appSwitcherBtn");
    if (!btn) return;
    var switcher = document.getElementById("appSwitcher");
    btn.addEventListener("click", function(e) {
        e.stopPropagation();
        var isOpen = switcher.classList.toggle("open");
        btn.setAttribute("aria-expanded", String(isOpen));
    });
    document.addEventListener("click", function(e) {
        if (!switcher.contains(e.target)) {
            switcher.classList.remove("open");
            btn.setAttribute("aria-expanded", "false");
        }
    });
    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            switcher.classList.remove("open");
            btn.setAttribute("aria-expanded", "false");
        }
    });
})();
