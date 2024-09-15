(function($) {

	"use strict";


})(jQuery);
function showHideShopName() {
    var tipoDropdown = document.getElementById("tipo");
    var shopNameField = document.getElementById("shopNameField");

    if (tipoDropdown.value === "merchant") {
        shopNameField.style.display = "block";
    } else {
        shopNameField.style.display = "none";
    }
}