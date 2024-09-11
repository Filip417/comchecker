document.addEventListener('DOMContentLoaded', function() {

  // For Create.html drag and drop image field
// Get elements
const dropzoneLabel = document.getElementById('dropzone-label');
const filePreview = document.getElementById('file-preview');
const fileIcon = document.getElementById('file-icon');
const fileInput = document.getElementById('dropzone-file');

// Function to handle file selection
function handleFile(file) {
    // Update file preview image
    const reader = new FileReader();
    reader.onload = function(e) {
        filePreview.src = e.target.result;
        filePreview.classList.remove('hidden'); // Show image preview
        fileIcon.classList.add('hidden'); // Hide SVG icon
    };
    reader.readAsDataURL(file);

    // Update file name display
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-description').textContent = '';
}

// Handle drag over event
dropzoneLabel.addEventListener('dragover', function(e) {
    e.preventDefault();
    dropzoneLabel.classList.add('border-blue-500'); // Example: Highlight drop zone on drag over
});

// Handle drag leave event
dropzoneLabel.addEventListener('dragleave', function(e) {
    e.preventDefault();
    dropzoneLabel.classList.remove('border-blue-500'); // Example: Remove highlight on drag leave
});

// Handle drop event
dropzoneLabel.addEventListener('drop', function(e) {
    e.preventDefault();
    dropzoneLabel.classList.remove('border-blue-500'); // Example: Remove highlight on drop

    const file = e.dataTransfer.files[0];
    if (file) {
        handleFile(file);
    }
});

// Listen for change event on file input
fileInput.addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        handleFile(file);
    }
});




});