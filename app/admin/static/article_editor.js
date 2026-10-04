document.addEventListener('DOMContentLoaded', function () {
  const field = document.querySelector('textarea[name="content_html"]');
  if (!field || !window.Jodit) return;

  const editor = window.Jodit.make(field, {
    height: 620,
    minHeight: 380,
    toolbarAdaptive: true,
    buttons: ['bold', 'italic', 'underline', '|', 'ul', 'ol', '|', 'paragraph', 'fontsize', '|', 'link', 'image', 'table', '|', 'align', 'undo', 'redo', '|', 'source', 'fullsize'],
    buttonsMD: ['bold', 'italic', 'ul', 'ol', 'paragraph', 'link', 'image', 'table', 'source', 'fullsize'],
    buttonsSM: ['bold', 'italic', 'ul', 'ol', 'paragraph', 'link', 'source', 'fullsize'],
    uploader: { insertImageAsBase64URI: false },
    askBeforePasteHTML: false,
    defaultActionOnPaste: 'insert_as_html',
    placeholder: 'Viết nội dung bài viết tại đây...',
  });

  const form = field.closest('form');
  if (form) form.addEventListener('submit', function () {
    field.value = editor.value;
  });
});
