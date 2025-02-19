// Countdown Timer Script
function startCountdown(targetDate) {
    const countdownInterval = setInterval(() => {
        const now = new Date().getTime();
        const distance = targetDate - now;

        if (distance <= 0) {
            clearInterval(countdownInterval);
            const countdownElement = document.getElementById('countdown');
            if (countdownElement) {
                countdownElement.innerHTML = "The event has started!";
            } else {
                console.warn("Countdown element not found.");
            }
            return;
        }

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        const daysElement = document.getElementById('days');
        if (daysElement) {
            daysElement.textContent = days.toString().padStart(2, '0');
        }

        const hoursElement = document.getElementById('hours');
        if (hoursElement) {
            hoursElement.textContent = hours.toString().padStart(2, '0');
        }

        const minutesElement = document.getElementById('minutes');
        if (minutesElement) {
            minutesElement.textContent = minutes.toString().padStart(2, '0');
        }

        const secondsElement = document.getElementById('seconds');
        if (secondsElement) {
            secondsElement.textContent = seconds.toString().padStart(2, '0');
        }
    }, 1000);
}

// Example: Set countdown to February 20, 2025
const eventDate = new Date('February 25, 2025 00:00:00').getTime();
startCountdown(eventDate);

// Declare these variables in the global scope
let selectedEvents = [];
let currentEventSelection = null;

document.addEventListener("DOMContentLoaded", function () {
    // Declare and initialize addEventBtn and other required elements.
    const addEventBtn = document.getElementById("add-event-btn");
    const categorySelect = document.getElementById("category");
    const eventsContainer = document.getElementById("events-container");
    const groupSizeContainer = document.getElementById("group-size-container");
    const groupSizeInput = document.getElementById("group-size");
    const teamMembersContainer = document.getElementById("team-members-container");
    const memberInputsContainer = document.getElementById("member-inputs");
    // ...existing variable declarations...

    function validateMemberInputs() {
        const memberInputs = document.querySelectorAll("#member-inputs input");
        let isValid = true;
        memberInputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                input.classList.add('invalid');
            } else {
                input.classList.remove('invalid');
            }
        });
        return isValid;
    }

    // Modified add event button handler
    if (addEventBtn) {
        addEventBtn.addEventListener("click", function() {
            if (!currentEventSelection) {
                console.log('No event selected');
                return;
            }

            // Validate team members if it's a team event
            if (currentEventSelection.type === "team" || currentEventSelection.type === "group") {
                if (!validateMemberInputs()) {
                    alert("Please fill in all team member names!");
                    return;
                }
            }

            const eventDetails = {
                category: categorySelect.value,
                event: currentEventSelection.name,
                type: currentEventSelection.type,
                cost: currentEventSelection.cost,
                members: []
            };

            if (currentEventSelection.type === "team" || currentEventSelection.type === "group") {
                const memberInputs = document.querySelectorAll("#member-inputs input");
                memberInputs.forEach(input => {
                    if (input.value.trim()) {
                        eventDetails.members.push(input.value.trim());
                    }
                });
            }

            selectedEvents.push(eventDetails);
            updateSelectedEventsList();
            updateTotalCost();
            
            // Only reset event selection radio buttons
            const radioInputs = document.querySelectorAll('input[name="event"]');
            radioInputs.forEach(input => input.checked = false);
            
            // Reset member inputs but keep sections visible
            if (memberInputsContainer) {
                memberInputsContainer.innerHTML = '';
            }
            
            currentEventSelection = null;
            addEventBtn.disabled = true;

            // Keep sections visible
            selectedEventsSection.classList.remove("hidden");
            personalDetailsSection.classList.remove("hidden");
        });
    }

    // Modified event radio button change handler
    categorySelect.addEventListener("change", function () {
        // ...existing category change code...

        events[selectedCategory].forEach(event => {
            // ...existing event option creation code...

            input.addEventListener("change", function () {
                currentEventSelection = event;
                addEventBtn.disabled = false;
                
                // Always show and reset group size for team events
                if (event.type === "team" || event.type === "group") {
                    groupSizeContainer.classList.remove("hidden");
                    teamMembersContainer.classList.remove("hidden");
                    groupSizeInput.value = event.minTeam || 1;
                    generateMemberInputs(parseInt(groupSizeInput.value));
                } else {
                    groupSizeContainer.classList.add("hidden");
                    teamMembersContainer.classList.add("hidden");
                }
            });
        });
    });

    // Add validation styles
    const additionalStyles = `
        .invalid {
            border-color: #ff0000 !important;
            box-shadow: 0 0 5px rgba(255, 0, 0, 0.5);
        }

        .member-input input {
            transition: all 0.3s ease;
        }

        .member-input input:required {
            border-left: 3px solid #ff4500;
        }
    `;

    const styleSheet = document.createElement("style");
    styleSheet.innerText = additionalStyles;
    document.head.appendChild(styleSheet);
});

const events = {
    tech: [
        
    ],
    cultural: [
        // ...existing cultural events...
    ],
    management: [
        { name: "Vagmita (Elocution)", type: "individual", cost: 200 },
        { name: "DAKSH (THE BEST MANAGER)", type: "individual", cost: 300 },
        { name: "SHRESHTA VITTA (FINANCE) Final", type: "team", cost: 400, minTeam: 2, maxTeam: 3 },
        { name: "SHRESHTA VITTA (FINANCE) Preliminary", type: "team", cost: 200, minTeam: 2, maxTeam: 3 },
        { name: "MANAVA SANSADHAN (HR)", type: "team", cost: 300, minTeam: 2, maxTeam: 3 },
        { name: "Startup Logo Design", type: "individual", cost: 150 },
        { name: "Business Plan", type: "team", cost: 350, minTeam: 2, maxTeam: 4 },
        { name: "Marketing Strategy", type: "team", cost: 300, minTeam: 2, maxTeam: 3 }
    ]
};
