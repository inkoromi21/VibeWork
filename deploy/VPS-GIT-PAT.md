# Git на VPS: Fine-grained Personal Access Token (HTTPS)

Чтобы `git pull` на сервере **не спрашивал логин/пароль**, используйте PAT и один из способов ниже.

## Токен в GitHub

1. **Settings → Developer settings → Fine-grained personal access tokens**.
2. **Resource owner** — ваш пользователь или организация.
3. **Repository access** — только репозиторий VibeWork (или All, если нужно).
4. **Permissions → Repository permissions → Contents: Read-only** (для `git pull` достаточно чтения; для `push` нужен Read and write).

Скопируйте токен сразу после создания (потом его не покажут).

## Способ A (рекомендуется): сохранить логин один раз

На **VPS**, в каталоге репозитория (например `/opt/vibework`):

```bash
cd /opt/vibework
git config credential.helper store
git pull origin main
```

Когда Git спросит:

- **Username** — ваш **логин GitHub** (не e-mail).
- **Password** — **вставьте PAT** (целиком, как пароль).

После успешного pull строка попадёт в `~/.git-credentials`, следующие `git pull` будут без вопросов.

Права на файл:

```bash
chmod 600 ~/.git-credentials
```

## Способ B: URL с токеном (быстро, но токен виден в `git config`)

```bash
cd /opt/vibework
git remote set-url origin "https://ВАШ_GITHUB_LOGIN:ВАШ_PAT@github.com/ВЛАДЕЛЕЦ/VibeWork.git"
```

Не коммитьте и не публикуйте этот URL. При смене токена обновите `remote` снова.

Для Fine-grained PAT в качестве «пароля» в URL используется **сам токен**; username — **ваш GitHub login**.

## Проверка

```bash
cd /opt/vibework
git remote -v
git pull origin main
```

Должно пройти без запроса имени пользователя.

## С ПК одной командой (без сохранения PAT на VPS)

Скрипт **`deploy/vps-full-update.ps1`** копирует `.env`, делает `git pull` по URL с Fine-grained PAT и перезапускает сервисы. Перед запуском в PowerShell:

```powershell
$env:VIBEWORK_GITHUB_USER = "ваш_логин_github"
$env:VIBEWORK_GITHUB_PAT  = "github_pat_..."
cd d:\fork\VibeWork   # корень репозитория
.\deploy\vps-full-update.ps1
```

Репозиторий `owner/repo` берётся из `git remote origin` на ПК; при необходимости укажите `-GitHubRepo "owner/VibeWork"`. SSH к VPS по ключу: `-IdentityFile "$env:USERPROFILE\.ssh\id_ed25519"`.

## Скрипты только на VPS

`deploy/vps-update.sh` не вызывает `git pull`. Если делаете pull вручную на сервере без скрипта с ПК — настройте PAT на VPS (способ A или B выше).
