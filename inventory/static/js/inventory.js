document.addEventListener('DOMContentLoaded', function () {
    // 1. Toast Initialization
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    toastElList.map(function (toastEl) {
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();
    });

    // 1.5 Mobile Camera QR Scanner Integration
    const tagInput = document.getElementById('company_tag_input');
    const cameraBtn = document.getElementById('camera-trigger-btn');
    const helperText = document.getElementById('helper-text');
    const readerContainer = document.getElementById('qr-reader-container');
    const closeScannerBtn = document.getElementById('close-scanner-btn');
    const auditForm = document.getElementById('audit-form');

    let html5QrCode = null;
    const isMobile = /Mobi|Android|iPhone/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 0 && window.innerWidth <= 992);

    if (cameraBtn && tagInput) {
        if (isMobile) {
            cameraBtn.classList.remove('d-none');
            tagInput.placeholder = "Tap to scan QR code or type tag...";
            if (helperText) {
                helperText.textContent = "Tap the input field or camera icon to open live QR scanner.";
            }

            tagInput.addEventListener('click', startScanner);
            cameraBtn.addEventListener('click', startScanner);
        } else {
            // Ensure camera button stays hidden on desktop
            cameraBtn.classList.add('d-none');
        }
    }

    function startScanner() {
        if (!readerContainer) return;
        readerContainer.style.display = 'block';
        if (!html5QrCode) {
            html5QrCode = new Html5Qrcode("reader");
        }

        html5QrCode.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: { width: 250, height: 250 }
            },
            (decodedText, decodedResult) => {
                if (tagInput) tagInput.value = decodedText;
                stopScanner();
                if (auditForm) auditForm.submit();
            },
            (errorMessage) => {
                // Scanning frame search loop (safe to ignore)
            }
        ).catch((err) => {
            console.error("Unable to start scanning.", err);
            alert("Camera access denied or not available.");
            readerContainer.style.display = 'none';
        });
    }

    function stopScanner() {
        if (!readerContainer) return;
        if (html5QrCode && html5QrCode.isScanning) {
            html5QrCode.stop().then(() => {
                readerContainer.style.display = 'none';
            }).catch(err => {
                console.error("Failed to stop scanning.", err);
            });
        } else {
            readerContainer.style.display = 'none';
        }
    }

    if (closeScannerBtn) {
        closeScannerBtn.addEventListener('click', stopScanner);
    }

    // 2. Add Asset Modal Dynamic Field Toggle Logic
    const assetTypeSelect = document.getElementById('modal_asset_type');
    if (assetTypeSelect) {
        assetTypeSelect.addEventListener('change', function () {
            const selectedType = this.value;
            const specSection = document.getElementById('modal-specifications-section');
            const allSpecFields = document.querySelectorAll('.modal-spec-field');
            const laptopFields = document.querySelectorAll('.modal-laptop-spec');
            const brandField = document.querySelector('.modal-brand-field');
            const modelField = document.querySelector('.modal-model-field');

            if (selectedType) {
                specSection.style.display = 'block';
            } else {
                specSection.style.display = 'none';
                return;
            }

            allSpecFields.forEach(field => {
                field.style.display = 'none';
                const input = field.querySelector('input');
                if (input) input.removeAttribute('required');
            });

            if (selectedType === 'LAPTOP') {
                brandField.style.display = 'block';
                modelField.style.display = 'block';
                laptopFields.forEach(field => field.style.display = 'block');

                brandField.querySelector('input').setAttribute('required', 'required');
                modelField.querySelector('input').setAttribute('required', 'required');
                document.querySelector('input[name="ram"]').setAttribute('required', 'required');
                document.querySelector('input[name="cpu"]').setAttribute('required', 'required');
            } 
            else if (selectedType === 'MONITOR' || selectedType === 'CELLPHONE') {
                brandField.style.display = 'block';
                modelField.style.display = 'block';

                brandField.querySelector('input').setAttribute('required', 'required');
                modelField.querySelector('input').setAttribute('required', 'required');
            } 
            else if (selectedType === 'OTHERS') {
                brandField.style.display = 'block';
                brandField.querySelector('input').setAttribute('required', 'required');
            }
        });
    }

    // 3. Export PNG Toast Notification Handler
    const exportBtn = document.getElementById('export-qr-btn');
    const toastContainer = document.querySelector('.toast-container');

    if (exportBtn && toastContainer) {
        exportBtn.addEventListener('click', function () {
            const toastHtml = `
                <div class="toast align-items-center text-white bg-success border-0 shadow" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex">
                        <div class="toast-body fs-6 fw-semibold">
                            <i class="bi bi-check-circle me-2"></i>QRCode PNG file generated
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                </div>
            `;

            toastContainer.insertAdjacentHTML('beforeend', toastHtml);
            const newToastEl = toastContainer.lastElementChild;
            const bsToast = new bootstrap.Toast(newToastEl, { delay: 4000 });
            bsToast.show();

            newToastEl.addEventListener('hidden.bs.toast', function () {
                newToastEl.remove();
            });
        });
    }

    // 4. Live Auto-Search Script
    const searchBar = document.getElementById('search-bar');
    if (searchBar) {
        let searchTimeout;
        searchBar.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value;
            const searchUrl = searchBar.dataset.searchUrl || '';

            searchTimeout = setTimeout(() => {
                fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('inventory-table-body');
                    tbody.innerHTML = '';

                    if (data.assets.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted py-4"><i class="bi bi-search fs-3 d-block mb-2"></i>No assets found matching "${query}".</td></tr>`;
                        return;
                    }

                    data.assets.forEach(item => {
                        const qrCell = item.qr_code_url 
                            ? `<div class="bg-white p-1 d-inline-block border rounded shadow-sm">
                                <img src="${item.qr_code_url}" class="qr-img" alt="QR Code">
                               </div>` 
                            : `<span class="text-muted small">No QR</span>`;

                        let statusBadgeClass = 'bg-primary';
                        if (item.status === 'AVAILABLE') statusBadgeClass = 'bg-success';
                        else if (item.status === 'UNDER_REPAIR') statusBadgeClass = 'bg-warning text-dark';
                        else if (item.status === 'DISPOSED') statusBadgeClass = 'bg-danger';

                        function truncateText(text, maxLength = 25) {
                            if (!text) return '';
                            return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
                        }

                        let actionsCellContent = '';
                        if (item.latest_remark) {
                            const truncatedRemark = truncateText(item.latest_remark, 25);
                            actionsCellContent = `
                                <div class="text-start p-1 bg-light rounded border small">
                                    <div class="fw-bold text-success mb-1"><i class="bi bi-journal-check me-1"></i>Last Remarks:</div>
                                    <p class="mb-1 text-wrap text-break" style="max-width: 220px;" title="${item.latest_remark}">
                                        "${truncatedRemark}"
                                    </p>
                                    <div class="text-muted text-end" style="font-size: 0.725rem;">&mdash; ${item.latest_auditor} (${item.latest_audit_date})</div>
                                </div>`;
                        } else {
                            actionsCellContent = `
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#editModal${item.id}"><i class="bi bi-pencil-square"></i> Edit</button>
                                    <button type="button" class="btn btn-outline-danger" data-bs-toggle="modal" data-bs-target="#deleteModal${item.id}"><i class="bi bi-trash"></i> Delete</button>
                                </div>`;
                        }

                        tbody.innerHTML += `
                            <tr>
                                <td data-label="Company Tag"><span class="font-monospace fw-bold text-primary">${item.company_tag}</span></td>
                                <td data-label="Unit Name" class="fw-medium">${item.unit_name}</td>
                                <td data-label="Serial Number"><small class="font-monospace text-muted">${item.serial_number}</small></td>
                                <td data-label="Assigned To">${item.assigned_to ? `<i class="bi bi-person me-1 text-secondary"></i>${item.assigned_to}` : '<span class="text-muted fst-italic">Unassigned</span>'}</td>
                                <td data-label="Status"><span class="badge ${statusBadgeClass}">${item.status_display || item.status}</span></td>
                                <td data-label="Date Added" class="small text-muted">${item.date_added}</td>
                                <td data-label="Date Updated" class="small text-muted">${item.date_updated}</td>
                                <td data-label="QR Code" class="no-print text-center">${qrCell}</td>
                                <td data-label="Actions" class="no-print text-center">${actionsCellContent}</td>
                            </tr>
                        `;
                    });
                });
            }, 300);
        });
    }
});