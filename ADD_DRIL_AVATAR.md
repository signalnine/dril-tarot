# Adding Dril's Profile Picture to Tweet Mockups

## Step 1: Download Dril's Profile Picture

Visit dril's profile and save the profile image:

**Option A: From Twitter/X directly**
1. Go to https://x.com/dril (or https://twitter.com/dril)
2. Right-click on the profile picture
3. Select "Save image as..."
4. Save as `dril_avatar.jpg` in the `dril-tarot/` directory

**Option B: Direct URL (may change over time)**
The current profile picture URL follows this pattern:
```
https://pbs.twimg.com/profile_images/[id]/[filename]
```

You can find the current URL by:
1. Opening https://x.com/dril in your browser
2. Right-clicking the profile picture
3. Selecting "Open image in new tab"
4. Copying that URL

## Step 2: Convert to Base64

Run the converter script:

```bash
python3 utils/download_dril_avatar.py dril_avatar.jpg
```

This will:
- Resize the image to 48x48 pixels
- Convert it to base64
- Print the base64 string to copy
- Save it to `data/dril_avatar_base64.txt`

## Step 3: Update the Script

The converter will output a line like:
```python
avatar_placeholder = "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
```

Copy this line and replace line 80 in `generate_dril_tarot_images.py`:

**Before:**
```python
avatar_placeholder = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4..."
```

**After:**
```python
avatar_placeholder = "data:image/jpeg;base64,/9j/4AAQSkZJRg..."  # Actual dril avatar
```

## Step 4: Regenerate Gallery

Regenerate the tweet screenshots with the new avatar:

```bash
python3 generate_dril_tarot_images.py --regenerate-screenshots --card-images-dir tarot-cards
```

The `--regenerate-screenshots` flag forces new tweet screenshots with the updated profile picture.

---

**Note:** Profile pictures are the property of their owners. Using dril's profile picture
in this context (displaying it alongside dril's own tweets in a transformative artistic work)
is generally considered fair use, but please be respectful of attribution.
