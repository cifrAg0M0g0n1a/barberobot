let dateInput, timeSlotsContainer, serviceNameEl, servicePriceEl, addressEl;
let nameInput, phoneInput, bookBtn, statusEl, promoCodeInput;
let selectedTime = null;
let userId = null;
let username = null;
let address = null;



if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.expand();

    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        userId = tg.initDataUnsafe.user.id;
        username = tg.initDataUnsafe.user.username || null;
    }
}

async function loadConfig() {
    try {
        const serviceRes = await fetch("/service");
        const service = await serviceRes.json();
        if (serviceNameEl) serviceNameEl.textContent = service.name;
        if (servicePriceEl) servicePriceEl.textContent = service.price + " ₽";

        const addressRes = await fetch("/address");
        const data = await addressRes.json();
        address = data.address;
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

    if (!date) {
        timeSlotsContainer.innerHTML = `
            <div class="time-placeholder">
                Выберите дату
            </div>
        `;
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
        timeSlotsContainer.innerHTML = `
            <div class="time-placeholder">
                Ошибка загрузки времени
            </div>
        `;
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

    if (address == null) {
        statusEl.textContent = "Не удалось создать запись, так как адрес отсутствует";
        statusEl.style.color = "#dc3545";
        return;
    }

    let price = null;

    try {
        const serviceRes = await fetch("/service");
        const service = await serviceRes.json();
        price = service.price;
    } catch (e) {
        console.error("Ошибка загрузки конфигурации:", e);
        if (serviceNameEl) serviceNameEl.textContent = "Ошибка";
        if (servicePriceEl) servicePriceEl.textContent = "Ошибка";
        if (addressEl) addressEl.textContent = "Ошибка";
        price = -1;
    }

    const data = {
        date: dateInput.value,
        time: selectedTime,
        name: nameInput.value,
        phone: phoneInput.value,
        userId: userId,
        username: username,
        address: address,
        price: price,
    };

    if (promoCodeInput && promoCodeInput.value.trim()) {
        data.promo_code = promoCodeInput.value.trim();
    }

    if (!phoneInput.value.match(/^\+7 \(\d{3}\) \d{3} \d{2}-\d{2}$/)) {
        statusEl.textContent = "Введите номер в формате +7 (000) 000 00-00";
        statusEl.style.color = "#dc3545";
        return;
    }

    try {
        const res = await fetch("/add_record", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.detail || "Ошибка при записи");
        }

        dateInput.value = "";
        nameInput.value = "";
        phoneInput.value = "";
        if (promoCodeInput) promoCodeInput.value = "";
        selectedTime = null;

        timeSlotsContainer.innerHTML = `
            <div class="time-placeholder">
                Выберите дату
            </div>
        `;

        statusEl.textContent = result.message || "Запись успешно добавлена!";
        statusEl.style.color = "#28a745";
    } catch (e) {
        console.error("Ошибка при записи:", e);
        const errorMessage = e.message || "При записи произошла ошибка. Повторите позже";
        statusEl.textContent = errorMessage;
        statusEl.style.color = "#dc3545";

        if (errorMessage.includes("промокод") && promoCodeInput) {
            promoCodeInput.value = "";
        }
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
    promoCodeInput = document.getElementById("promoCode");
    bookBtn = document.getElementById("submitBtn");
    statusEl = document.getElementById("status");

    if (!dateInput || !timeSlotsContainer || !serviceNameEl || !servicePriceEl ||
        !addressEl || !nameInput || !phoneInput || !bookBtn || !statusEl || !promoCodeInput) {
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

    timeSlotsContainer.innerHTML = `
        <div class="time-placeholder">
            Выберите дату
        </div>
    `;

    const today = new Date();
    today.setDate(today.getDate());
    dateInput.min = today.toISOString().split("T")[0];

    const maskOptions = {
        mask: '+{7} (000) 000 00-00'
    };
    IMask(phoneInput, maskOptions);

    dateInput.addEventListener("change", (e) => updateSlots(e.target.value));
    bookBtn.addEventListener("click", addRecord);

    loadConfig();
});