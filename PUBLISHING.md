#!/usr/bin/env bash
# ============================================================
# PYPI PUBLISHING GUIDE
# Run each block manually — do not run this entire file at once.
# Each section is labeled with what it does and why.
# ============================================================

# ============================================================
# PHASE 1: PREPARE — Run these once before your first publish
# ============================================================

# Install the tools needed to build and upload your package.
# "build" creates the distribution files.
# "twine" uploads them securely.
pip install build twine

# ============================================================
# PHASE 2: BUILD — Run this every time before publishing
# ============================================================

# This creates two files in the dist/ folder:
#   murm-0.1.0.tar.gz     — source distribution
#   murm-0.1.0-py3-none-any.whl — wheel (installable directly)
# The version number comes from pyproject.toml.
python -m build

# Verify the contents look correct before uploading.
# You should see both the .tar.gz and .whl files.
ls -la dist/

# ============================================================
# PHASE 3: TESTPYPI — Upload here first. It is a sandbox.
# ============================================================

# Step 1: Create a TestPyPI account
# Go to: https://test.pypi.org/account/register/
# Verify your email.
# Enable two-factor authentication (Settings > Two factor authentication).

# Step 2: Create a TestPyPI API token
# Go to: https://test.pypi.org/manage/account/token/
# Click "Add API token"
# Name: "murm-test"
# Scope: "Entire account" for your first upload
# COPY the token immediately — it starts with pypi- and is shown only once.

# Step 3: Upload to TestPyPI
# When prompted for username: type __token__ (literally, with underscores)
# When prompted for password: paste the token you just copied
twine upload --repository testpypi dist/*

# Step 4: Verify the upload
# Go to: https://test.pypi.org/project/murm/
# You should see your package page.

# Step 5: Test that it installs correctly from TestPyPI
# Do this in a fresh terminal with a clean virtual environment:
python3 -m venv /tmp/murm_test_install
source /tmp/murm_test_install/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            murm
murm --help
deactivate
rm -rf /tmp/murm_test_install

# If "murm --help" shows the command menu, the package works correctly.

# ============================================================
# PHASE 4: PYPI — Upload to the real package index
# ============================================================

# Step 1: Create a PyPI account
# Go to: https://pypi.org/account/register/
# Verify email. Enable two-factor authentication.
# Note: this is a separate account from TestPyPI.

# Step 2: Create a PyPI API token
# Go to: https://pypi.org/manage/account/token/
# Name: "murm-release"
# Scope: "Entire account" for first upload, then narrow to project after first upload
# Copy the token immediately.

# Step 3: Create a .pypirc file to store credentials (optional but convenient)
# This avoids typing your token every time.
# WARNING: This file contains your secret token. Keep it private.
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_REAL_PYPI_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN_HERE
EOF

# Restrict permissions so only you can read it:
chmod 600 ~/.pypirc

# Step 4: Upload to PyPI
twine upload dist/*
# If you created .pypirc above, it won't ask for credentials.
# If you didn't, enter __token__ as username and your token as password.

# Step 5: Verify the upload
# Go to: https://pypi.org/project/murm/

# Step 6: Test the final install
python3 -m venv /tmp/murm_final_test
source /tmp/murm_final_test/bin/activate
pip install murm
murm --help
deactivate
rm -rf /tmp/murm_final_test

# ============================================================
# PHASE 5: RELEASING A NEW VERSION
# ============================================================

# Every time you make changes and want to publish a new version:

# Step 1: Update the version in pyproject.toml
# Change: version = "0.1.0"
# To:     version = "0.2.0"
# Use semantic versioning: major.minor.patch
#   Patch (0.1.1): bug fixes only
#   Minor (0.2.0): new features, backward compatible
#   Major (1.0.0): breaking changes

# Step 2: Commit the version bump
git add pyproject.toml
git commit -m "Release v0.2.0"

# Step 3: Create and push a version tag
git tag v0.2.0
git push origin main
git push origin v0.2.0

# The GitHub Actions workflow (in .github/workflows/release.yml) will
# automatically build and upload to PyPI when it sees a new tag.
# You do not need to run "twine upload" manually if you have the
# PYPI_API_TOKEN secret set in your GitHub repository settings.

# To set the secret in GitHub:
# 1. Go to your repository on github.com
# 2. Settings > Secrets and variables > Actions
# 3. Click "New repository secret"
# 4. Name: PYPI_API_TOKEN
# 5. Value: paste your PyPI token
# 6. Click "Add secret"

# ============================================================
# TROUBLESHOOTING
# ============================================================

# "File already exists" error
# You cannot overwrite an existing version on PyPI.
# You must bump the version number and rebuild.

# "Invalid or non-existent authentication" error
# Your token is wrong or expired. Go to PyPI > Account settings > API tokens
# and create a new one.

# "The user ... isn't allowed to upload to project ..."
# Your token scope is set to a different project. Create a new token with
# "Entire account" scope, or scope it specifically to "murm".

# Package not found after upload
# PyPI takes 2-5 minutes to index new uploads.
# TestPyPI takes up to 10 minutes. Wait and try again.

# "Legacy non-reproducible build" warning
# This is safe to ignore. It just means the .tar.gz has a timestamp.
