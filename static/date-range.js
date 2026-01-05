// Date Range Selection Functionality

document.addEventListener("DOMContentLoaded", function() {
    // Variables for date range selection
    var startDate = null;
    var endDate = null;
    var selectedDates = [];
    var isSelectingRange = false;

    // Handle date click for range selection
    function handleDateClick(e) {
        var dateElement = e.target.closest('.calendar-day');
        if (!dateElement || dateElement.classList.contains('booked')) {
            return;
        }

        var dateStr = dateElement.getAttribute('date');
        var dateObj = new Date(dateStr);

        // If we already have a start date and this is the same date, clear selection
        if (startDate && dateStr === startDate) {
            clearSelection();
            return;
        }

        // If we have a start date but no end date, set end date
        if (startDate && !endDate) {
            // Don't allow selecting a date before the start date
            if (dateObj < new Date(startDate)) {
                return;
            }
            endDate = dateStr;
            dateElement.classList.add('end-date');
            updateRangeSelection();
            fetchPriceForRange();
            return;
        }

        // If we have both start and end dates, start a new selection
        if (startDate && endDate) {
            clearSelection();
        }

        // Set start date
        startDate = dateStr;
        dateElement.classList.add('start-date');
        isSelectingRange = true;
        updateSelectionInfo();
    }

    // Update the visual range selection
    function updateRangeSelection() {
        if (!startDate || !endDate) return;

        // Clear previous range selection
        var rangeSelectedDays = document.querySelectorAll('.calendar-day.range-selected');
        rangeSelectedDays.forEach(function(day) {
            day.classList.remove('range-selected');
        });

        // Convert dates to comparable format
        var start = new Date(startDate);
        var end = new Date(endDate);

        // Add range-selected class to all days between start and end
        var current = new Date(start);
        while (current <= end) {
            var currentStr = current.getFullYear() + "-" +
                ((current.getMonth() + 1) < 10 ? "0" : "") + (current.getMonth() + 1) + "-" +
                (current.getDate() < 10 ? "0" : "") + current.getDate();

            var dayElement = document.querySelector('.calendar-day[date="' + currentStr + '"]');
            if (dayElement && !dayElement.classList.contains('booked')) {
                dayElement.classList.add('range-selected');
            }

            current.setDate(current.getDate() + 1);
        }

        updateSelectionInfo();
    }

    // Update the selection info text
    function updateSelectionInfo() {
        var selectionInfo = document.getElementById('selectionInfo');
        var selectionText = document.getElementById('selectionText');

        if (startDate && endDate) {
            var start = new Date(startDate);
            var end = new Date(endDate);
            var days = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;

            selectionText.textContent = startDate + ' → ' + endDate + ' (' + days + ' nuit' + (days > 1 ? 's' : '') + ')';
            selectionInfo.style.display = 'block';
        } else if (startDate) {
            selectionText.textContent = 'Début: ' + startDate + ' - Sélectionnez la fin';
            selectionInfo.style.display = 'block';
        } else {
            selectionInfo.style.display = 'none';
        }
    }

    // Clear all selections
    function clearSelection() {
        startDate = null;
        endDate = null;
        selectedDates = [];

        // Remove all selection classes
        var selectedDays = document.querySelectorAll('.calendar-day.start-date, .calendar-day.end-date, .calendar-day.range-selected');
        selectedDays.forEach(function(day) {
            day.classList.remove('start-date', 'end-date', 'range-selected');
        });

        // Hide price and selection info
        document.getElementById('priceDisplay').style.display = 'none';
        document.getElementById('selectionInfo').style.display = 'none';
    }

    // Fetch price from backend for the selected date range
    function fetchPriceForRange() {
        if (!startDate || !endDate) return;

        // Check if the selected range includes any booked dates
        var start = new Date(startDate);
        var end = new Date(endDate);
        var hasBookedDates = false;

        var current = new Date(start);
        while (current <= end) {
            var currentStr = current.getFullYear() + "-" +
                ((current.getMonth() + 1) < 10 ? "0" : "") + (current.getMonth() + 1) + "-" +
                (current.getDate() < 10 ? "0" : "") + current.getDate();

            var dayElement = document.querySelector('.calendar-day[date="' + currentStr + '"]');
            if (dayElement && dayElement.classList.contains('booked')) {
                hasBookedDates = true;
                break;
            }

            current.setDate(current.getDate() + 1);
        }

        // Show loading state
        var priceDisplay = document.getElementById('priceDisplay');
        var priceAmount = document.getElementById('priceAmount');
        var priceDetails = document.getElementById('priceDetails');
        var selectionInfo = document.getElementById('selectionInfo');
        var selectionText = document.getElementById('selectionText');

        if (hasBookedDates) {
            selectionText.textContent = 'Période non disponible - contient des dates réservées';
            selectionInfo.style.display = 'block';
            priceDisplay.style.display = 'none';
            priceDetails.textContent = '';
            return;
        }

        priceAmount.textContent = 'Calcul en cours...';
        priceDisplay.style.display = 'block';

        // Make API call to backend
        fetch('/api/get-price', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                priceAmount.textContent = data.total_price + ' €';
                if (data.details) {
                    priceDetails.textContent = data.details;
                } else {
                    priceDetails.textContent = '';
                }
            } else {
                priceAmount.textContent = 'Prix indisponible, contactez le propriètaire pour plus d\'informations';
                priceDetails.textContent = '';
            }
        })
        .catch(error => {
            console.error('Error fetching price:', error);
            priceAmount.textContent = 'Erreur lors de la récupération du prix';
            priceDetails.textContent = '';
        });
    }

    // Add event listeners to calendar days
    function addDateClickListeners() {
        var calendarDays = document.querySelectorAll('.calendar-day');
        calendarDays.forEach(function(day) {
            day.addEventListener('click', handleDateClick);
        });
    }

    // Initialize date click listeners
    addDateClickListeners();

    // Re-attach listeners when calendar is redrawn
    window.addEventListener('calendarRedrawn', function() {
        addDateClickListeners();
        // Reapply selection state after calendar is redrawn
        restoreSelectionState();
    });

    // Restore selection state after calendar redraw
    function restoreSelectionState() {
        // If we have a start date, apply the start-date class
        if (startDate) {
            var startDayElement = document.querySelector('.calendar-day[date="' + startDate + '"]');
            if (startDayElement && !startDayElement.classList.contains('booked')) {
                startDayElement.classList.add('start-date');
            }
        }

        // If we have an end date, apply the end-date class
        if (endDate) {
            var endDayElement = document.querySelector('.calendar-day[date="' + endDate + '"]');
            if (endDayElement && !endDayElement.classList.contains('booked')) {
                endDayElement.classList.add('end-date');
            }
        }

        // Reapply range selection if both dates are set
        if (startDate && endDate) {
            updateRangeSelection();
        }

        // Restore selection info display
        updateSelectionInfo();
    }
});
