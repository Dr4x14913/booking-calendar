// Address autocomplete functionality using OpenStreetMap Nominatim API

document.addEventListener('DOMContentLoaded', function() {
    const addressInput = document.getElementById('address');
    const suggestionsContainer = document.getElementById('address-suggestions');

    if (!addressInput || !suggestionsContainer) return;

    // Debounce function to limit API calls
    function debounce(func, delay) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Fetch address suggestions from Nominatim API
    async function fetchAddressSuggestions(query) {
        if (query.length < 3) {
            suggestionsContainer.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&addressdetails=1&limit=3`);

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            displaySuggestions(data);
        } catch (error) {
            console.error('Error fetching address suggestions:', error);
            suggestionsContainer.innerHTML = '<div class="suggestion-item">Aucune suggestion trouvée</div>';
        }
    }

    // Display suggestions in the dropdown
    function displaySuggestions(suggestions) {
        console.log(suggestions);
        if (suggestions.length === 0) {
            suggestionsContainer.innerHTML = '<div class="suggestion-item">Aucune suggestion trouvée</div>';
            return;
        }

        suggestionsContainer.innerHTML = suggestions
            .map(suggestion => `
                <div class="suggestion-item" data-lat="${suggestion.lat}" data-lon="${suggestion.lon}" data-display="${escapeHtml(suggestion.display_name)}">
                    ${escapeHtml(suggestion.display_name)}
                </div>
            `)
            .join('');

        // Add click event to each suggestion
        document.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', function() {
                addressInput.value = this.getAttribute('data-display');
                suggestionsContainer.innerHTML = '';

                // Store coordinates in hidden fields if they exist
                const latInput = document.createElement('input');
                latInput.type = 'hidden';
                latInput.name = 'address_lat';
                latInput.value = this.getAttribute('data-lat');
                form.appendChild(latInput);

                const lonInput = document.createElement('input');
                lonInput.type = 'hidden';
                lonInput.name = 'address_lon';
                lonInput.value = this.getAttribute('data-lon');
                form.appendChild(lonInput);
            });
        });
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Event listeners
    addressInput.addEventListener('input', debounce(function(e) {
        fetchAddressSuggestions(e.target.value);
    }, 300));

    // Close suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!addressInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.innerHTML = '';
        }
    });

    // Close suggestions when pressing Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            suggestionsContainer.innerHTML = '';
        }
    });
});
