// Автоматическая загрузка предложений при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.replacement-block').forEach(block => {
        const lessonId = block.dataset.lessonId;
        const day = block.dataset.day;  // Добавьте data-day в HTML
        const subject = block.dataset.subject;  // Добавьте data-subject в HTML
        fetchSuggestions(lessonId, day, subject);
    });
});

// Запрос предложений
function fetchSuggestions(lessonId, day, subject) {
    console.log(`fetchSuggestions called with ${lessonId}, ${day}, ${subject}`);

    fetch(`/replacements/api/suggestions/?lesson_id=${lessonId}&day=${encodeURIComponent(day)}&subject=${encodeURIComponent(subject)}`)
        .then(response => response.json())
        .then(data => {
            const teacherSpan = document.getElementById(`suggestedTeacher_${lessonId}`);
            const select = document.getElementById(`select_${lessonId}`);

            if (data.teachers && data.teachers.length > 0) {
                const teacher = data.teachers[0];
                teacherSpan.textContent = teacher.name;

                // Заполняем селект
                select.innerHTML = "";
                data.teachers.forEach(t => {
                    const option = document.createElement("option");
                    option.value = t.id;
                    option.textContent = t.name;
                    select.appendChild(option);
                });
            } else {
                teacherSpan.textContent = "Нет подходящих учителей";
                select.innerHTML = "";
            }
        })
        .catch(error => {
            console.error("Ошибка при получении учителей:", error);
            const teacherSpan = document.getElementById(`suggestedTeacher_${lessonId}`);
            if (teacherSpan) teacherSpan.textContent = "Ошибка загрузки";
        });
}


function populateCustomSelect(lessonId, teachers) {
    const select = document.querySelector(`#select_${lessonId}`);
    select.innerHTML = teachers.map(t =>
        `<option value="${t.id}">${t.name}</option>`
    ).join('');
    select.closest('.custom-selection').style.display = 'block';
}

// Сохранение замены
function saveReplacement(lessonId) {
    const teacherId = document.querySelector(`#select_${lessonId}`).value;
    fetch('/replacements/api/save_replacement/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({lesson_id: lessonId, teacher_id: teacherId})
    }).then(response => alert('Сохранено!'));
}

// Добавление нового учителя для замены
function addAnotherTeacher() {
    window.location.href = '/replacements/';
}