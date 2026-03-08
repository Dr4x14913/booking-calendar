// Date Range Selection Functionality

document.addEventListener("DOMContentLoaded", function() {
    // Variables for date range selection
    var startDate = null;
    var endDate = null;
    var selectedDates = [];
    var isSelectingRange = false;
    var allowedStartDates = [];
    var forbiddenEndDates = [];
    var bookedDatesAfterStart = [];
    var bookedDatesFetched = false;

    // Handle date click for range selection
    function handleDateClick(e) {
        var dateElement = e.target.closest('.calendar-day');
        if (!dateElement || dateElement.classList.contains('booked') || dateElement.classList.contains('disabled')) {
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
            // Don't allow selecting a booked date or dates after the first booked date
            var bookedDay = document.querySelector('.calendar-day[date="' + dateStr + '"].booked');
            if (bookedDay) {
                return;
            }
            endDate = dateStr;
            dateElement.classList.add('end-date');
            updateRangeSelection();
            fetchPriceForRange();
            showReservationButton();
            return;
        }

        // If we have both start and end dates, check if we're selecting a new start date
        if (startDate && endDate) {
            // Don't allow selecting a date before the current start date
            if (dateObj < new Date(startDate)) {
                return;
            }
            clearSelection();
        }

        // Only allow selecting dates that are in the allowed start dates list
        if (allowedStartDates.length > 0 && !allowedStartDates.includes(dateStr)) {
            return;
        }

        // Set start date
        startDate = dateStr;
        dateElement.classList.add('start-date');
        isSelectingRange = true;
        updateSelectionInfo();

        // Fetch forbidden end dates for this start date
        fetchForbiddenEndDates(dateStr);

        // Disable dates before the start date and forbidden end dates
        disableDatesBeforeStart();

        // Fetch and disable booked dates that come after the start date
        fetchAndDisableBookedDates();
    }

    // Disable dates before the start date and forbidden end dates
    function disableDatesBeforeStart() {
        var calendarDays = document.querySelectorAll('.calendar-day');
        calendarDays.forEach(function(day) {
            var dateStr = day.getAttribute('date');
            if (dateStr && startDate) {
                var dateObj = new Date(dateStr);
                var startObj = new Date(startDate);

                // If date is before start date and not already booked, disable it
                if (dateObj < startObj && !day.classList.contains('booked')) {
                    day.classList.add('disabled');
                } else if (dateObj >= startObj && day.classList.contains('disabled')) {
                    // Re-enable dates that are on or after start date
                    // But keep forbidden end dates disabled
                    if (!forbiddenEndDates.includes(dateStr)) {
                        day.classList.remove('disabled');
                    }
                }
            }
        });

        // Disable forbidden end dates
        if (forbiddenEndDates.length > 0 && startDate) {
            forbiddenEndDates.forEach(function(forbiddenDate) {
                var forbiddenDay = document.querySelector('.calendar-day[date="' + forbiddenDate + '"]');
                if (forbiddenDay && !forbiddenDay.classList.contains('booked')) {
                    forbiddenDay.classList.add('disabled');
                }
            });
        }
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

    // Fetch allowed start dates from backend
    function fetchAllowedStartDates() {
        fetch('/api/get-allowed-start-dates')
            .then(response => response.json())
            .then(data => {
                allowedStartDates = data;
                disableNonAllowedStartDates();
            })
            .catch(error => {
                console.error('Error fetching allowed start dates:', error);
            });
    }

    // Disable dates that are not in the allowed start dates list
    function disableNonAllowedStartDates() {
        if (allowedStartDates.length === 0) return;

        var calendarDays = document.querySelectorAll('.calendar-day');
        calendarDays.forEach(function(day) {
            var dateStr = day.getAttribute('date');
            if (dateStr && !day.classList.contains('booked') && !allowedStartDates.includes(dateStr)) {
                day.classList.add('disabled');
            }
        });
    }

    // Fetch forbidden end dates for a given start date
    function fetchForbiddenEndDates(startDateStr) {
        forbiddenEndDates = []; // Reset forbidden dates

        fetch('/api/get-forbidden-end-dates?start_date=' + startDateStr)
            .then(response => response.json())
            .then(data => {
                forbiddenEndDates = data;
                // Reapply date disabling to include forbidden end dates
                disableDatesBeforeStart();
            })
            .catch(error => {
                console.error('Error fetching forbidden end dates:', error);
            });
    }

    // Fetch all booked dates and disable them after a start date is selected
    function fetchAndDisableBookedDates() {
        if (!startDate) return;

        fetch('/api/get-booked-dates')
            .then(response => response.json())
            .then(bookedDates => {
                bookedDatesFetched = true;
                var startObj = new Date(startDate);

                // Find the first booked date that comes after the start date
                var firstBookedAfterStart = null;
                var firstBookedAfterStartStr = null;
                bookedDates.forEach(function(bookedDateStr) {
                    var bookedDate = new Date(bookedDateStr);
                    if (bookedDate > startObj) {
                        if (firstBookedAfterStart === null || bookedDate < firstBookedAfterStart) {
                            firstBookedAfterStart = bookedDate;
                            firstBookedAfterStartStr = bookedDateStr;
                        }
                    }
                });

                // Store all booked dates after start for validation
                bookedDatesAfterStart = [];
                bookedDates.forEach(function(bookedDateStr) {
                    var bookedDate = new Date(bookedDateStr);
                    if (bookedDate >= startObj) {
                        bookedDatesAfterStart.push(bookedDateStr);
                    }
                });

                // If we found a booked date after the start, disable all dates from that booked date onward
                if (firstBookedAfterStart) {
                    var calendarDays = document.querySelectorAll('.calendar-day');
                    calendarDays.forEach(function(day) {
                        var dateStr = day.getAttribute('date');
                        if (dateStr) {
                            var dateObj = new Date(dateStr);
                            // Disable the booked date and all dates after it
                            if (dateObj >= firstBookedAfterStart && !day.classList.contains('booked')) {
                                day.classList.add('disabled');
                            }
                        }
                    });
                    console.log(firstBookedAfterStart);
                    const firstBookedAfterStartElement = document.querySelector('[date="' + firstBookedAfterStartStr + '"]');
                    console.log(firstBookedAfterStartElement);
                    firstBookedAfterStartElement.classList.remove('disabled', "booked");
                    firstBookedAfterStartElement.classList.add('available', 'temp-available');
                    console.log(firstBookedAfterStartElement);
                }
            })
            .catch(error => {
                console.error('Error fetching booked dates:', error);
            });
    }

    // Clear all selections
    function clearSelection() {
        startDate = null;
        endDate = null;
        selectedDates = [];
        forbiddenEndDates = [];

        // Remove all selection classes
        var selectedDays = document.querySelectorAll('.calendar-day.start-date, .calendar-day.end-date, .calendar-day.range-selected');
        selectedDays.forEach(function(day) {
            day.classList.remove('start-date', 'end-date', 'range-selected');
        });

        // Re-enable all dates (except those that are actually booked)
        var allDays = document.querySelectorAll('.calendar-day');
        allDays.forEach(function(day) {
            // Only remove disabled class if the date is not actually booked
            if (!day.classList.contains('booked')) {
                day.classList.remove('disabled');
            }
            if (day.classList.contains('temp-available')){
              day.classList.remove('temp-available', 'available');
              day.classList.add('booked');
            }
        });

        // Reapply allowed start dates restriction
        disableNonAllowedStartDates();

        // Hide price and selection info
        document.getElementById('priceDisplay').style.display = 'none';
        document.getElementById('selectionInfo').style.display = 'none';
        hideReservationButton();
    }

    // Show reservation button when date range is selected
    function showReservationButton() {
        var reservationButton = document.getElementById('reservationButton');
        if (reservationButton) {
            reservationButton.href = '/reservation-form?start_date=' + startDate + '&end_date=' + endDate;
            reservationButton.style.display = 'inline-block';
        }
    }

    // Hide reservation button
    function hideReservationButton() {
        var reservationButton = document.getElementById('reservationButton');
        if (reservationButton) {
            reservationButton.style.display = 'none';
        }
    }

    // Fetch price from backend for the selected date range
    function fetchPriceForRange() {
        if (!startDate || !endDate) return;

        // Show loading state
        var priceDisplay = document.getElementById('priceDisplay');
        var priceAmount = document.getElementById('priceAmount');
        var priceDetails = document.getElementById('priceDetails');

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

    // Fetch allowed start dates when page loads
    fetchAllowedStartDates();

    // Re-attach listeners when calendar is redrawn
    window.addEventListener('calendarRedrawn', function() {
        addDateClickListeners();
        // Reapply selection state after calendar is redrawn
        restoreSelectionState();
        // Reapply disabled states for allowed start dates
        disableNonAllowedStartDates();
        // Reapply disabled states for forbidden end dates if we have a start date
        if (startDate) {
            disableDatesBeforeStart();
            fetchAndDisableBookedDates();
        }
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
