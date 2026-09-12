# API Request Documentation

Документация эндпоинтов приложений **accounts** и **main**, а также способы тестирования через Postman.

**Base URL:** `http://127.0.0.1:8000`

**Auth:** JWT Bearer (`Authorization: Bearer <access_token>`)

---

## Настройка Postman

### 1. Создать коллекцию и переменные

1. Создайте коллекцию `APP-NEWS`.
2. Откройте **Collection → Variables** и добавьте:

| Variable       | Initial Value                      | Current Value |
|----------------|------------------------------------|---------------|
| `base_url`     | `http://127.0.0.1:8000`            | то же         |
| `access_token` | *(пусто)*                          | заполняется после login/register |
| `refresh_token`| *(пусто)*                          | заполняется после login/register |
| `post_slug`    | *(пусто)*                          | slug созданного поста |
| `category_slug`| *(пусто)*                          | slug категории |

В URL запросов используйте: `{{base_url}}/api/v1/...`

### 2. Авторизация в Postman

Для защищённых эндпоинтов:

1. Вкладка **Authorization**
2. Type → **Bearer Token**
3. Token → `{{access_token}}`

Либо вручную в Headers:

```
Authorization: Bearer {{access_token}}
```

### 3. Автосохранение токенов (Tests script)

В запросах **Register** и **Login** на вкладке **Tests** добавьте:

```javascript
if (pm.response.code === 200 || pm.response.code === 201) {
    const json = pm.response.json();
    if (json.access) {
        pm.collectionVariables.set("access_token", json.access);
    }
    if (json.refresh) {
        pm.collectionVariables.set("refresh_token", json.refresh);
    }
}
```

После успешного входа/регистрации токены попадут в переменные коллекции.

### 4. Body в Postman

- JSON: **Body → raw → JSON**
- Файлы (avatar, image): **Body → form-data**

### 5. Порядок тестирования

1. Register / Login → получить токены  
2. Profile, Change Password  
3. Categories (создать → список → детали)  
4. Posts (создать → список → детали → my-posts)  
5. Popular / Recent / Posts by category  
6. Token Refresh → Logout  

---

## Accounts (`/api/v1/auth/`)

### 1. Register — регистрация

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `{{base_url}}/api/v1/auth/register/` |
| **Auth** | Не требуется |

**Body (JSON):**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "StrongPass123!",
  "password_confirm": "StrongPass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Ожидаемый ответ:** `201 Created` — объект `user`, `access`, `refresh`, `message`.

**Postman:** Body → raw → JSON. Добавьте Tests-скрипт для сохранения токенов.

---

### 2. Login — вход

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `{{base_url}}/api/v1/auth/login/` |
| **Auth** | Не требуется |

**Body (JSON):**

```json
{
  "email": "john@example.com",
  "password": "StrongPass123!"
}
```

**Ожидаемый ответ:** `200 OK` — `user`, `access`, `refresh`, `message`.

**Postman:** Body → raw → JSON + Tests-скрипт для токенов.

---

### 3. Logout — выход

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `{{base_url}}/api/v1/auth/logout/` |
| **Auth** | Bearer `{{access_token}}` |

**Body (JSON):**

```json
{
  "refresh_token": "{{refresh_token}}"
}
```

**Ожидаемый ответ:** `200 OK` — `{"message": "Logou successful"}`  
При невалидном токене: `400` — `{"error": "Invalid token"}`.

**Postman:** Authorization → Bearer Token → `{{access_token}}`.

---

### 4. Profile — профиль (GET / PUT / PATCH)

| | |
|---|---|
| **Method** | `GET` / `PUT` / `PATCH` |
| **URL** | `{{base_url}}/api/v1/auth/profile/` |
| **Auth** | Bearer `{{access_token}}` |

**GET** — получить профиль (без body).

**PUT / PATCH — Body (JSON):**

```json
{
  "first_name": "John",
  "last_name": "Updated",
  "bio": "About me"
}
```

Для аватара: **Body → form-data**:

| Key    | Type | Value        |
|--------|------|--------------|
| `bio`  | Text | About me     |
| `avatar` | File | выбрать файл |

**Ожидаемый ответ:** `200 OK` — данные профиля.

---

### 5. Change Password — смена пароля

| | |
|---|---|
| **Method** | `PUT` |
| **URL** | `{{base_url}}/api/v1/auth/change-password/` |
| **Auth** | Bearer `{{access_token}}` |

**Body (JSON):**

```json
{
  "old_password": "StrongPass123!",
  "new_password": "NewStrongPass456!",
  "new_password_confirm": "NewStrongPass456!"
}
```

**Ожидаемый ответ:** `200 OK` — `{"message": "Password updated successfully."}`.

---

### 6. Token Refresh — обновление access-токена

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `{{base_url}}/api/v1/auth/token/refresh/` |
| **Auth** | Не требуется |

**Body (JSON):**

```json
{
  "refresh": "{{refresh_token}}"
}
```

**Ожидаемый ответ:** `200 OK` — новый `access` (и при rotation — новый `refresh`).

**Postman Tests (сохранить новый access):**

```javascript
if (pm.response.code === 200) {
    const json = pm.response.json();
    if (json.access) {
        pm.collectionVariables.set("access_token", json.access);
    }
    if (json.refresh) {
        pm.collectionVariables.set("refresh_token", json.refresh);
    }
}
```

---

## Main (`/api/v1/posts/`)

Права:

- Чтение (GET) — часто без авторизации (опубликованные посты).
- Создание / изменение / удаление — нужен JWT.
- Черновики (`draft`) видит только автор.
- Редактировать/удалять пост может только автор.

### 7. List / Create Categories — категории

| | |
|---|---|
| **Method** | `GET` / `POST` |
| **URL** | `{{base_url}}/api/v1/posts/categories/` |
| **Auth** | GET — без токена; POST — Bearer |

**Query (GET, опционально):**

| Param     | Пример        | Описание              |
|-----------|---------------|-----------------------|
| `search`  | `tech`        | поиск по name/description |
| `ordering`| `name` / `-created_at` | сортировка     |

**POST Body (JSON):**

```json
{
  "name": "Technology",
  "description": "Tech news and reviews"
}
```

`slug` создаётся автоматически из `name`.

**Postman:** после создания сохраните slug:

```javascript
if (pm.response.code === 201) {
    const json = pm.response.json();
    if (json.slug) {
        pm.collectionVariables.set("category_slug", json.slug);
    }
}
```

---

### 8. Category Detail — детали / обновление / удаление категории

| | |
|---|---|
| **Method** | `GET` / `PUT` / `PATCH` / `DELETE` |
| **URL** | `{{base_url}}/api/v1/posts/categories/{{category_slug}}/` |
| **Auth** | GET — без токена; изменение/удаление — Bearer |

**PUT / PATCH Body (JSON):**

```json
{
  "name": "Technology Updated",
  "description": "Updated description"
}
```

---

### 9. Posts by Category — посты категории

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/posts/categories/{{category_slug}}/posts/` |
| **Auth** | Не требуется |

**Ожидаемый ответ:** `200 OK`:

```json
{
  "category": { "...": "..." },
  "posts": [ "..."]
}
```

Возвращаются только посты со статусом `published`.

---

### 10. List / Create Posts — список и создание постов

| | |
|---|---|
| **Method** | `GET` / `POST` |
| **URL** | `{{base_url}}/api/v1/posts/` |
| **Auth** | GET — без токена (published); POST — Bearer |

**Query (GET, опционально):**

| Param      | Пример              | Описание                          |
|------------|---------------------|-----------------------------------|
| `category` | `1`                 | ID категории                      |
| `author`   | `1`                 | ID автора                         |
| `status`   | `published` / `draft` | статус (для своего аккаунта)    |
| `search`   | `django`            | поиск по title/content            |
| `ordering` | `-views_count`      | сортировка                        |
| `page`     | `1`                 | пагинация (по 20)                 |

**POST Body (JSON):**

```json
{
  "title": "My First Post",
  "content": "Full post content here...",
  "category": 1,
  "status": "published"
}
```

С изображением — **form-data**:

| Key        | Type | Value              |
|------------|------|--------------------|
| `title`    | Text | My First Post      |
| `content`  | Text | Full post content  |
| `category` | Text | `1`                |
| `status`   | Text | `published`        |
| `image`    | File | выбрать файл       |

`author` и `slug` выставляются на сервере.

**Postman Tests (сохранить slug поста):**

```javascript
if (pm.response.code === 201) {
    const json = pm.response.json();
    if (json.slug) {
        pm.collectionVariables.set("post_slug", json.slug);
    }
}
```

---

### 11. My Posts — мои посты

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/posts/my-posts/` |
| **Auth** | Bearer `{{access_token}}` |

**Query:** `category`, `status`, `search`, `ordering`, `page`.

---

### 12. Popular Posts — популярные

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/posts/popular` |
| **Auth** | Не требуется |

До 10 опубликованных постов, сортировка по `-views_count`.

---

### 13. Recent Posts — свежие

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/posts/recent` |
| **Auth** | Не требуется |

До 10 опубликованных постов, сортировка по `-created_at`.

---

### 14. Post Detail — детали / обновление / удаление поста

| | |
|---|---|
| **Method** | `GET` / `PUT` / `PATCH` / `DELETE` |
| **URL** | `{{base_url}}/api/v1/posts/{{post_slug}}/` |
| **Auth** | GET — без токена; изменение/удаление — Bearer (только автор) |

При `GET` увеличивается `views_count`.

**PUT / PATCH Body (JSON):**

```json
{
  "title": "Updated Title",
  "content": "Updated content...",
  "category": 1,
  "status": "draft"
}
```

**DELETE:** ожидание `204 No Content`.

---

## Краткая шпаргалка эндпоинтов

### Accounts

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/auth/register/` | — |
| POST | `/api/v1/auth/login/` | — |
| POST | `/api/v1/auth/logout/` | JWT |
| GET/PUT/PATCH | `/api/v1/auth/profile/` | JWT |
| PUT | `/api/v1/auth/change-password/` | JWT |
| POST | `/api/v1/auth/token/refresh/` | — |

### Main

| Method | Endpoint | Auth |
|--------|----------|------|
| GET/POST | `/api/v1/posts/categories/` | POST → JWT |
| GET/PUT/PATCH/DELETE | `/api/v1/posts/categories/<slug>/` | write → JWT |
| GET | `/api/v1/posts/categories/<slug>/posts/` | — |
| GET/POST | `/api/v1/posts/` | POST → JWT |
| GET | `/api/v1/posts/my-posts/` | JWT |
| GET | `/api/v1/posts/popular` | — |
| GET | `/api/v1/posts/recent` | — |
| GET/PUT/PATCH/DELETE | `/api/v1/posts/<slug>/` | write → автор |

---

## Чек-лист в Postman

1. Запустите сервер: `python manage.py runserver`
2. Создайте коллекцию и переменные (`base_url`, `access_token`, `refresh_token`, …)
3. **Register** → проверьте `201` и сохранение токенов
4. **Login** → `200`, токены обновлены
5. **Profile GET** → `200` с данными пользователя
6. **Profile PATCH** → био обновлено
7. **Create Category** → `201`, сохраните `category_slug`
8. **Create Post** → `201`, сохраните `post_slug`
9. **List Posts** → есть новый пост
10. **My Posts** → пост в списке
11. **Post Detail GET** → `views_count` растёт
12. **Popular / Recent** → `200`
13. **Posts by Category** → пост в категории
14. **Token Refresh** → новый `access`
15. **Logout** → `200`, старый refresh больше не работает
