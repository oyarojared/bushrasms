document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("studentSearchInput");
  const searchShortcut = document.getElementById("searchShortcut");

  // Search field may not exist for non-admin users
  if (!searchInput) {
    return;
  }

  /*
   * Update the visual shortcut depending on the operating system.
   */
  if (searchShortcut) {
    const isMac = /Mac|iPhone|iPad|iPod/i.test(navigator.platform);

    searchShortcut.textContent = isMac ? "⌘ K" : "Ctrl K";
  }

  /*
   * Ctrl + K / Command + K
   *
   * Focus the student search field.
   */
  document.addEventListener("keydown", function (event) {
    const isShortcut =
      (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";

    if (!isShortcut) {
      return;
    }

    /*
     * Don't hijack Ctrl/Cmd + K when the user
     * is already typing in another editable element.
     */
    const activeElement = document.activeElement;

    const isTyping =
      activeElement &&
      (activeElement.tagName === "INPUT" ||
        activeElement.tagName === "TEXTAREA" ||
        activeElement.tagName === "SELECT" ||
        activeElement.isContentEditable);

    /*
     * If already inside the search field, allow
     * normal browser/OS behavior.
     */
    if (activeElement === searchInput) {
      return;
    }

    /*
     * Focus our search field.
     */
    event.preventDefault();

    searchInput.focus();

    /*
     * Put cursor at the end of existing text.
     */
    const valueLength = searchInput.value.length;

    try {
      searchInput.setSelectionRange(valueLength, valueLength);
    } catch (error) {
      // Some input types may not support selection ranges.
    }
  });
});
