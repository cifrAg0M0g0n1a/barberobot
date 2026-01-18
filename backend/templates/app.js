let dateInput, timeSlotsContainer, serviceNameEl, servicePriceEl, addressEl;
let nameInput, phoneInput, bookBtn, statusEl;
let selectedTime = null;
let userId = null;



if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.expand();

    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        userId = tg.initDataUnsafe.user.id;
    }
}

async function loadConfig() {
    try {
        const serviceRes = await fetch("/service");
        const service = await serviceRes.json();
        if (serviceNameEl) serviceNameEl.textContent = service.name;
        if (servicePriceEl) servicePriceEl.textContent = service.price + " ₽";

        const addressRes = await fetch("/address");
        const address = await addressRes.text();
        if (addressEl) addressEl.textContent = address;
    } catch (e) {
        console.error("Ошибка загрузки конфигурации:", e);
        if (serviceNameEl) serviceNameEl.textContent = "Ошибка";
        if (servicePriceEl) servicePriceEl.textContent = "Ошибка";
        if (addressEl) addressEl.textContent = "Ошибка";
    }
}

async function updateSlots(date) {
    if (!timeSlotsContainer) {
        console.error("timeSlotsContainer не найден");
        return;
    }

    try {
        const res = await fetch(`/slots?date=${date}`);
        const slots = await res.json();

        timeSlotsContainer.innerHTML = "";
        selectedTime = null;

        slots.forEach(slot => {
            const div = document.createElement("div");
            div.textContent = slot.time;
            div.className = "time-slot" + (slot.available ? "" : " disabled");

            if (slot.available) {
                div.addEventListener("click", () => {
                    document.querySelectorAll(".time-slot.selected").forEach(el => el.classList.remove("selected"));
                    div.classList.add("selected");
                    selectedTime = slot.time;
                });
            }

            timeSlotsContainer.appendChild(div);
        });
    } catch (e) {
        console.error("Ошибка при получении слотов:", e);
        timeSlotsContainer.innerHTML = "Ошибка";
    }
}

async function addRecord() {
    if (!dateInput || !nameInput || !phoneInput || !statusEl) {
        console.error("Не все элементы доступны для отправки формы");
        return;
    }

    if (!dateInput.value || !selectedTime || !nameInput.value || !phoneInput.value) {
        statusEl.textContent = "Заполните все поля и выберите время";
        statusEl.style.color = "#dc3545";
        return;
    }

    const data = {
        date: dateInput.value,
        time: selectedTime,
        name: nameInput.value,
        phone: phoneInput.value,
        userId: userId,
    };

    try {
        const res = await fetch("/records", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        statusEl.textContent = result.message || "Запись успешно добавлена!";
        statusEl.style.color = "#28a745";
    } catch (e) {
        console.error("Ошибка при записи:", e);
        statusEl.textContent = "При записи произошла ошибка. Повторите позже";
        statusEl.style.color = "#dc3545";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM загружен, начинаем инициализацию");

    if (!userId) {
        document.body.innerHTML = `
            <div style="
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                font-family: Arial, sans-serif;
                padding: 20px;
            ">
                <div>
                    <h2>🚫 Запись недоступна</h2>
                    <p>
                        Запись на стрижку возможна <br>
                        <strong>только через Telegram-бота</strong>.
                    </p>
                    <a style="color: #777; font-size: 14px;" href="https://t.me/TimeToCut_bot">
                        Нажмите, чтобы перейти к боту
                    </a>
                </div>
            </div>
        `;
        return;
    }

    dateInput = document.getElementById("date");
    timeSlotsContainer = document.getElementById("timeSlots");
    serviceNameEl = document.getElementById("serviceName");
    servicePriceEl = document.getElementById("servicePrice");
    addressEl = document.getElementById("address");
    nameInput = document.getElementById("userName");
    phoneInput = document.getElementById("userPhone");
    bookBtn = document.getElementById("submitBtn");
    statusEl = document.getElementById("status");

    if (!dateInput || !timeSlotsContainer || !serviceNameEl || !servicePriceEl ||
        !addressEl || !nameInput || !phoneInput || !bookBtn || !statusEl) {
        console.error("Не все элементы найдены на странице");
        console.error("dateInput:", dateInput, "timeSlotsContainer:", timeSlotsContainer);
        document.body.innerHTML = `
            <div style="
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                font-family: Arial, sans-serif;
                padding: 20px;
            ">
                <div>
                    <h2>Произошла ошибка</h2>
                    <p>
                        Попробуйте перезагрузить страницу
                    </p>
                </div>
            </div>
        `;
        return;
    }

    dateInput.addEventListener("change", (e) => updateSlots(e.target.value));
    bookBtn.addEventListener("click", addRecord);

    loadConfig();
});