# 🚀 Git Cheatsheet (Practical Developer Guide)

---

## 🧠 Core Mental Model

```
Working Directory → Staging Area → Commit History → Remote
```

| Stage             | Meaning                 |
| ----------------- | ----------------------- |
| Working Directory | Your actual files       |
| Staging Area      | What you plan to commit |
| Commit History    | Saved snapshots         |
| Remote            | GitHub / server         |

---

## 🔍 1. Always Start Here (Most Important Commands)

```bash
git status
git log --oneline --graph --decorate
git diff
```

👉 Habit: **Run `git status` before every commit**

---

## 📦 2. Staging & Committing

```bash
git add .
git add file.cpp
git commit -m "message"
```

---

## 🔄 3. Undo Mistakes (CRITICAL)

### Undo last commit (keep changes)

```bash
git reset HEAD~1
```

### Undo last commit (keep staged)

```bash
git reset --soft HEAD~1
```

### Delete last commit completely ⚠️

```bash
git reset --hard HEAD~1
```

---

## 🌐 4. Working with Remote (GitHub)

```bash
git remote add origin <url>
git push -u origin main
git push
git pull
```

---

## 🔥 Undo AFTER pushing

### ✅ Safe way (recommended)

```bash
git revert HEAD
git push
```

### ⚠️ Dangerous (solo only)

```bash
git reset --hard HEAD~1
git push --force
```

---

## 📜 5. Inspect History

```bash
git log
git log --oneline --graph --decorate
git show <commit>
git log -p
git log --stat
```

---

## 📂 6. Track Changes in Files

```bash
git log file.cpp
git blame file.cpp
```

---

## 🔍 7. Compare Changes

```bash
git diff
git diff --staged
git diff commit1 commit2
```

---

## 🔀 8. Branching (Basics)

```bash
git branch
git branch new-branch
git checkout new-branch

# Modern way
git switch new-branch
```

---

## 🔧 9. Fix Staging Mistakes

### Unstage file

```bash
git restore --staged file.cpp
```

### Discard changes

```bash
git restore file.cpp
```

---

## ⚡ 10. Daily Workflow

```bash
git status
git add .
git commit -m "meaningful message"
git push
```

---

## 🧭 11. Navigation (Inside Git Screens)

When using `git log`, `git diff`, etc.:

```
q → quit
/ → search
n → next result
space → next page
```

---

## ⚠️ 12. Common Mistakes (Avoid These)

❌ Committing from wrong folder
✔ Always run: `git status`

❌ Forgetting to add files
✔ Use: `git add .`

❌ Using `--hard` casually
✔ Only if you're 100% sure

❌ Force pushing in team projects
✔ Prefer: `git revert`

---

## 🔥 13. Pro Tips

### Clean log view:

```bash
git log --oneline --graph --decorate --all
```

---

### Check what will be committed:

```bash
git diff --staged
```

---

### See last commit changes:

```bash
git show
```

---

## 🧠 Final Takeaway

> Git is not about memorizing commands — it’s about understanding change tracking.

If you master:

* `status`
* `add`
* `commit`
* `reset / revert`

👉 You’re already ahead of most developers.

---

## 🚀 Next Level (When You're Ready)

* Interactive rebase (`git rebase -i`)
* Squashing commits
* Cherry-pick
* Stashing changes

---

**Keep this file open while coding — within a week, most of this becomes muscle memory.**
