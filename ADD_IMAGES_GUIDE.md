# Adding Images to README

## Quick Steps

I've updated the README.md to reference two screenshots. Now you need to add the actual image files:

### 1. Save the Images

Save your two screenshots with these exact names:
- `docs/images/manual-sync-trigger.png` - The Manual Sync Trigger screenshot
- `docs/images/sync-job-details.png` - The Sync Job Details screenshot

### 2. Add to Git and Commit

```bash
# Make sure the images directory exists
mkdir -p docs/images

# Copy your images to the directory (replace with your actual file paths)
# Example if images are in Downloads:
# cp ~/Downloads/screenshot1.png docs/images/manual-sync-trigger.png
# cp ~/Downloads/screenshot2.png docs/images/sync-job-details.png

# Add the images and updated README to git
git add docs/images/manual-sync-trigger.png
git add docs/images/sync-job-details.png
git add README.md

# Commit
git commit -m "Add screenshots to README"

# Push to GitHub
git push origin main
```

## Alternative: Use Drag and Drop

If you prefer, you can:

1. Go to your GitHub repository
2. Navigate to `docs/images/` (create the folder if needed)
3. Click "Add file" → "Upload files"
4. Drag and drop your screenshots
5. Name them:
   - `manual-sync-trigger.png`
   - `sync-job-details.png`
6. Commit directly on GitHub

The README is already updated to reference these images!

## Image Names Reference

Based on the screenshots you showed:
- **First image** (Manual Sync Trigger page) → `manual-sync-trigger.png`
- **Second image** (Sync Job Details page) → `sync-job-details.png`

Once you add these images, they'll automatically appear in your README on GitHub! 🎉
