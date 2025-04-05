document.addEventListener("DOMContentLoaded", function() {
    const folders = document.querySelectorAll(".file-tree .folder");

    folders.forEach(folder => {
        folder.addEventListener("click", function() {
            const nextSibling = folder.nextElementSibling;
            if (nextSibling && nextSibling.tagName === "UL") {
                nextSibling.classList.toggle("hidden");
            }
        });
    });

    const checkboxes = document.querySelectorAll('.file-tree .checkbox');

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const parentLi = this.closest('li');
            const childCheckboxes = parentLi.querySelectorAll('ul .checkbox');
            childCheckboxes.forEach(childCheckbox => {
                childCheckbox.checked = this.checked;
            });
        });
    });
});
