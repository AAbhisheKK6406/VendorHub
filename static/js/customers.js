/* static/js/customers.js */

document.addEventListener('DOMContentLoaded', function () {
    console.log("Customer Management module interface initialized successfully.");

    const searchInput = document.getElementById('customer-search-input');
    const phoneFilterInput = document.getElementById('phone-filter-input');
    const emailFilterInput = document.getElementById('email-filter-input');

    if (searchInput) {
        searchInput.addEventListener('input', function (e) {
            const query = e.target.value.toLowerCase();
            console.log("Searching customers for query:", query);
        });
    }

    if (phoneFilterInput) {
        phoneFilterInput.addEventListener('input', function (e) {
            const phoneQuery = e.target.value.toLowerCase();
            console.log("Filtering customers by phone:", phoneQuery);
        });
    }

    if (emailFilterInput) {
        emailFilterInput.addEventListener('input', function (e) {
            const emailQuery = e.target.value.toLowerCase();
            console.log("Filtering customers by email:", emailQuery);
        });
    }
});