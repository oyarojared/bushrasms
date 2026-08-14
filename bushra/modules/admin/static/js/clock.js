function updateClock() {
  const clock = document.getElementById("clock");

  const now = new Date();

  // Format day names
  const days = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
  ];
  const dayName = days[now.getDay()];

  // Format date
  const date = now.toLocaleDateString(); // e.g. 12/1/2025

  // Format time
  const time = now.toLocaleTimeString(); // e.g. 10:43:09 AM

  // Display
  clock.textContent = `${dayName}, ${date} — ${time}`;
}

// Update clock every second
setInterval(updateClock, 1000);

// Run immediately on load
updateClock();
