/* static/js/reports.js */

document.addEventListener('DOMContentLoaded', function () {
    console.log("Reports & Analytics module interface initialized successfully.");

    const reportType = document.getElementById('reportType');
    const fromDate = document.getElementById('fromDate');
    const toDate = document.getElementById('toDate');
    const searchReportBtn = document.getElementById('searchReportBtn');
    const resetReportBtn = document.getElementById('resetReportBtn');
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    const printReportBtn = document.getElementById('printReportBtn');

    if (reportType) {
        reportType.addEventListener('change', function (e) {
            console.log("Selected report type changed to:", e.target.value);
        });
    }

    if (fromDate && toDate) {
        fromDate.addEventListener('change', function () {
            console.log("From date selected:", fromDate.value);
        });
        toDate.addEventListener('change', function () {
            console.log("To date selected:", toDate.value);
        });
    }
});