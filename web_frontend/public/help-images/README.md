# Help Images Directory

This directory contains screenshots and images for the help manual.

## Directory Structure

```
help-images/
├── quick-start/     # Images for Quick Start section
├── workflow/        # Images for Full Workflow Demo section
├── retargeter/      # Images for Retargeter section
├── player/          # Images for Player section
└── toolbox/         # Images for Toolbox section
```

## Image Guidelines

- **Format**: PNG or WebP for screenshots
- **Naming**: Use descriptive names (e.g., `upload-file-dialog.png`)
- **Size**: Optimize for web (max 1920px width, compressed)
- **Reference**: Use `/help-images/{section}/{filename}` in helpContent.tsx

## Example Usage

In `helpContent.tsx`:

```tsx
content: (
  <>
    <p>Description text...</p>
    <img src="/help-images/quick-start/upload-dialog.png" alt="上传文件对话框" />
  </>
)
```
