document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupAccessMessage = document.getElementById("signup-access-message");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("teacher-login-form");
  const logoutButton = document.getElementById("teacher-logout-button");
  const authStatus = document.getElementById("auth-status");
  const authMessage = document.getElementById("auth-message");
  let isTeacherAuthenticated = false;

  function setTeacherAuthenticated(authenticated, username = "") {
    isTeacherAuthenticated = authenticated;
    loginForm.classList.toggle("hidden", authenticated);
    logoutButton.classList.toggle("hidden", !authenticated);
    signupForm.classList.toggle("hidden", !authenticated);
    signupAccessMessage.classList.toggle("hidden", authenticated);
    authStatus.textContent = authenticated
      ? `Signed in as ${username}. You can manage registrations.`
      : "Sign in to manage student registrations. Activity details and participant lists are public.";
  }

  function showAuthMessage(message, className = "error") {
    authMessage.textContent = message;
    authMessage.className = `message ${className}`;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Activity request failed");
      }
      const activities = await response.json();
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft = details.max_participants - details.participants.length;

        const participantsHTML = details.participants.length > 0
          ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants.map((email) => `<li>
                  <span class="participant-email">${escapeHtml(email)}</span>
                  ${isTeacherAuthenticated
                    ? `<button class="delete-btn" type="button" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}" aria-label="Remove ${escapeHtml(email)} from ${escapeHtml(name)}">Remove</button>`
                    : ""}
                </li>`).join("")}
              </ul>
            </div>`
          : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">${participantsHTML}</div>
        `;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        await fetchActivities();
      } else {
        if (response.status === 401) {
          setTeacherAuthenticated(false);
          await fetchActivities();
        }
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");
      setTimeout(() => messageDiv.classList.add("hidden"), 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  async function restoreTeacherSession() {
    try {
      const response = await fetch("/auth/session");
      const session = await response.json();
      setTeacherAuthenticated(session.authenticated, session.username || "");
    } catch (error) {
      setTeacherAuthenticated(false);
      console.error("Error checking teacher session:", error);
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    authMessage.className = "message hidden";
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        showAuthMessage(result.detail || "Unable to sign in.");
        return;
      }

      loginForm.reset();
      setTeacherAuthenticated(true, result.username);
      showAuthMessage("Signed in successfully.", "success");
      await fetchActivities();
    } catch (error) {
      showAuthMessage("Unable to sign in. Please try again.");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } finally {
      setTeacherAuthenticated(false);
      authMessage.className = "message hidden";
      await fetchActivities();
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();
        await fetchActivities();
      } else {
        if (response.status === 401) {
          setTeacherAuthenticated(false);
          await fetchActivities();
        }
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");
      setTimeout(() => messageDiv.classList.add("hidden"), 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  restoreTeacherSession().then(fetchActivities);
});
