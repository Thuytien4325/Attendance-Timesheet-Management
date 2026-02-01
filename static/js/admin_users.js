// Xử lý vô hiệu hóa/kích hoạt lại nhân viên bằng fetch API
document.addEventListener("DOMContentLoaded", function () {
  function showAlert(type, message) {
    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
            <i class="bi ${type === "success" ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill"} me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
    document
      .querySelector(".container")
      .insertBefore(alertDiv, document.querySelector(".container").firstChild);
  }

  function updateStatus(row, isActive) {
    const statusBadge = row.querySelector("td:nth-last-child(2) .badge");
    if (!statusBadge) return;
    if (isActive) {
      statusBadge.className = "badge bg-success";
      statusBadge.textContent = "Active";
    } else {
      statusBadge.className = "badge bg-secondary";
      statusBadge.textContent = "Inactive";
    }
  }

  function replaceActionButton(row, isActive, userId, userName) {
    const actionCell = row.querySelector("td:last-child");
    if (!actionCell) return;

    if (isActive) {
      actionCell.innerHTML = `
                <button type="button" class="btn btn-sm btn-danger btn-deactivate-user" data-user-id="${userId}" data-user-name="${userName}">
                    <i class="bi bi-person-x-fill"></i> Vô hiệu hóa
                </button>
            `;
    } else {
      actionCell.innerHTML = `
                <button type="button" class="btn btn-sm btn-success btn-activate-user" data-user-id="${userId}" data-user-name="${userName}">
                    <i class="bi bi-person-check-fill"></i> Kích hoạt lại
                </button>
            `;
    }

    // Re-bind events for the newly injected button
    bindRowButtons(row);
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload || {}),
    }).then((r) => r.json());
  }

  function bindRowButtons(root) {
    const scope = root || document;

    scope.querySelectorAll(".btn-deactivate-user").forEach((button) => {
      button.addEventListener("click", function (e) {
        e.preventDefault();
        const userId = this.getAttribute("data-user-id");
        const userName = this.getAttribute("data-user-name");
        const buttonElement = this;
        if (
          !confirm(
            `Bạn có chắc chắn muốn vô hiệu hóa tài khoản của "${userName}"?`,
          )
        )
          return;

        buttonElement.disabled = true;
        buttonElement.innerHTML =
          '<i class="bi bi-hourglass-split"></i> Đang xử lý...';

        postJson(`/admin/users/delete/${userId}`, {})
          .then((data) => {
            if (data.success) {
              showAlert("success", data.message || "Đã vô hiệu hóa tài khoản!");
              const row = buttonElement.closest("tr");
              updateStatus(row, false);
              replaceActionButton(row, false, userId, userName);
            } else {
              showAlert(
                "danger",
                data.message || "Có lỗi xảy ra khi vô hiệu hóa nhân viên!",
              );
              buttonElement.disabled = false;
              buttonElement.innerHTML =
                '<i class="bi bi-person-x-fill"></i> Vô hiệu hóa';
            }
          })
          .catch((err) => {
            console.error("Error:", err);
            showAlert("danger", "Có lỗi xảy ra khi vô hiệu hóa nhân viên!");
            buttonElement.disabled = false;
            buttonElement.innerHTML =
              '<i class="bi bi-person-x-fill"></i> Vô hiệu hóa';
          });
      });
    });

    scope.querySelectorAll(".btn-activate-user").forEach((button) => {
      button.addEventListener("click", function (e) {
        e.preventDefault();
        const userId = this.getAttribute("data-user-id");
        const userName = this.getAttribute("data-user-name");
        const buttonElement = this;
        if (!confirm(`Kích hoạt lại tài khoản của "${userName}"?`)) return;

        buttonElement.disabled = true;
        buttonElement.innerHTML =
          '<i class="bi bi-hourglass-split"></i> Đang xử lý...';

        postJson(`/admin/users/activate/${userId}`, {})
          .then((data) => {
            if (data.success) {
              showAlert(
                "success",
                data.message || "Đã kích hoạt lại tài khoản!",
              );
              const row = buttonElement.closest("tr");
              updateStatus(row, true);
              replaceActionButton(row, true, userId, userName);
            } else {
              showAlert(
                "danger",
                data.message || "Có lỗi xảy ra khi kích hoạt lại!",
              );
              buttonElement.disabled = false;
              buttonElement.innerHTML =
                '<i class="bi bi-person-check-fill"></i> Kích hoạt lại';
            }
          })
          .catch((err) => {
            console.error("Error:", err);
            showAlert("danger", "Có lỗi xảy ra khi kích hoạt lại!");
            buttonElement.disabled = false;
            buttonElement.innerHTML =
              '<i class="bi bi-person-check-fill"></i> Kích hoạt lại';
          });
      });
    });
  }

  bindRowButtons(document);
});
