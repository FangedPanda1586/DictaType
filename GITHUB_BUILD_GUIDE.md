# Build DictaType on GitHub

## 1. Create the repository

1. Sign in to GitHub.
2. Select **New repository**.
3. Name it `DictaType`.
4. Choose **Public** for an open-source project, or **Private** while testing.
5. Do not add a README, `.gitignore`, or licence because this project already contains them.
6. Select **Create repository**.

## 2. Upload the project

1. Extract the downloaded ZIP.
2. Open the extracted `DictaType-GitHub-ready` folder.
3. In the empty GitHub repository, select **uploading an existing file** or **Add file > Upload files**.
4. Drag everything from inside the extracted folder into the upload page.
5. Confirm that the upload includes `.github`, `dictatype`, `tests`, `assets`, `README.md`, and the other project files.
6. Enter a commit message such as `Initial DictaType release`.
7. Select **Commit changes**.

The repository root must contain `.github/workflows/windows-build.yml`. Do not upload the whole project as a nested `DictaType-GitHub-ready` folder.

## 3. Run the Windows build

1. Open the repository's **Actions** tab.
2. Enable GitHub Actions if GitHub displays an enable button.
3. Select **Build Windows release** in the left sidebar.
4. Select **Run workflow**.
5. Keep the branch set to `main` and select the green **Run workflow** button.
6. Open the workflow run after it appears.
7. A green check mark means the tests, portable build, and installer build succeeded.

## 4. Download the application

1. Open the completed workflow run.
2. Scroll to **Artifacts**.
3. Select **DictaType-Windows**.
4. Extract the downloaded artifact ZIP.

It contains:

- `DictaType-Portable-Windows.zip`
- `DictaType-Setup.exe`

Use `DictaType-Setup.exe` for a normal Windows installation. Extract the portable ZIP to run `DictaType.exe` without installation.

## Troubleshooting

### The workflow is not visible

Check that this exact file exists in the repository:

```text
.github/workflows/windows-build.yml
```

It must be on the repository's default branch and at the repository root.

### There is no Run workflow button

Open **Actions**, select **Build Windows release**, and make sure the workflow is enabled. The `Run workflow` button is available because the file contains the `workflow_dispatch` trigger.

### A build step has a red X

Open the failed step to see its log. Use **Re-run jobs** after correcting the problem.

### Windows warns about the downloaded EXE

The open-source build is not digitally signed with a commercial code-signing certificate. Windows may therefore show a SmartScreen warning even when the source was built by your own GitHub workflow.
