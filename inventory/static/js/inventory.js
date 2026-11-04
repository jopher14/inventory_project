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
        let searchVersion = 0;

        function element(tag, className = '', value) {
            const node = document.createElement(tag);
            node.className = className;
            if (value !== undefined) node.textContent = String(value ?? '');
            return node;
        }

        // This project serves QR images from its own /media/ URLs.
        function safeImageUrl(value) {
            if (typeof value !== 'string' || !value.trim()) return null;
            try {
                const url = new URL(value, window.location.href);
                if (!['http:', 'https:'].includes(url.protocol)) return null;
                if (url.origin !== window.location.origin) return null;
                if (url.username || url.password) return null;
                return url.href;
            } catch {
                return null;
            }
        }

        function renderSearchResults(tbody, assets, query) {
            const fragment = document.createDocumentFragment();
            if (assets.length === 0) {
                const row = element('tr');
                const cell = element('td', 'text-center text-muted py-4');
                cell.colSpan = 9;
                cell.append(element('i', 'bi bi-search fs-3 d-block mb-2'));
                cell.append(document.createTextNode(`No assets found matching "${query}".`));
                row.append(cell);
                fragment.append(row);
            }

            assets.forEach(item => {
                const row = element('tr');
                function cell(label, className = '') {
                    const td = element('td', className);
                    td.dataset.label = label;
                    row.append(td);
                    return td;
                }
                cell('Company Tag').append(element('span', 'font-monospace fw-bold text-primary', item.company_tag));
                cell('Unit Name', 'fw-medium').textContent = item.unit_name ?? '';
                cell('Serial Number').append(element('small', 'font-monospace text-muted', item.serial_number));
                const assignee = cell('Assigned To');
                if (item.assigned_to) {
                    assignee.append(element('i', 'bi bi-person me-1 text-secondary'));
                    assignee.append(document.createTextNode(String(item.assigned_to)));
                } else {
                    assignee.append(element('span', 'text-muted fst-italic', 'Unassigned'));
                }
                const badgeClasses = {
                    AVAILABLE: 'bg-success',
                    UNDER_REPAIR: 'bg-warning text-dark',
                    DISPOSED: 'bg-danger',
                };
                const badgeClass = Object.hasOwn(badgeClasses, item.status)
                    ? badgeClasses[item.status] : 'bg-primary';
                cell('Status').append(element('span', `badge ${badgeClass}`, item.status_display || item.status));
                cell('Date Added', 'small text-muted').textContent = item.date_added ?? '';
                cell('Date Updated', 'small text-muted').textContent = item.date_updated ?? '';

                const qrCell = cell('QR Code', 'no-print text-center');
                const imageUrl = safeImageUrl(item.qr_code_url);
                if (imageUrl) {
                    const wrapper = element('div', 'bg-white p-1 d-inline-block border rounded shadow-sm');
                    const image = element('img', 'qr-img');
                    image.alt = 'QR Code';
                    image.src = imageUrl;
                    wrapper.append(image);
                    qrCell.append(wrapper);
                } else {
                    qrCell.append(element('span', 'text-muted small', 'No QR'));
                }

                const actions = cell('Actions', 'no-print text-center');
                if (item.latest_remark) {
                    const remark = String(item.latest_remark);
                    const box = element('div', 'text-start p-1 bg-light rounded border small');
                    const heading = element('div', 'fw-bold text-success mb-1');
                    heading.append(element('i', 'bi bi-journal-check me-1'));
                    heading.append(document.createTextNode('Last Remarks:'));
                    const paragraph = element('p', 'mb-1 text-wrap text-break',
                        `"${remark.length > 25 ? remark.substring(0, 25) + '...' : remark}"`);
                    paragraph.style.maxWidth = '220px';
                    paragraph.title = remark;
                    const attribution = element('div', 'text-muted text-end',
                        `— ${item.latest_auditor ?? ''} (${item.latest_audit_date ?? ''})`);
                    attribution.style.fontSize = '0.725rem';
                    box.append(heading, paragraph, attribution);
                    actions.append(box);
                } else if (Number.isSafeInteger(item.id) && item.id > 0) {
                    const group = element('div', 'btn-group btn-group-sm');
                    group.setAttribute('role', 'group');
                    for (const [action, style, icon] of [
                        ['Edit', 'primary', 'pencil-square'],
                        ['Delete', 'danger', 'trash'],
                    ]) {
                        const target = `#${action.toLowerCase()}Modal${item.id}`;
                        // Only show actions for modals available to this user.
                        if (!document.getElementById(target.slice(1))) continue;
                        const button = element('button', `btn btn-outline-${style}`);
                        button.type = 'button';
                        button.dataset.bsToggle = 'modal';
                        button.dataset.bsTarget = target;
                        button.append(element('i', `bi bi-${icon}`));
                        button.append(document.createTextNode(` ${action}`));
                        group.append(button);
                    }
                    actions.append(group);
                }
                fragment.append(row);
            });
            tbody.replaceChildren(fragment);
        }

        searchBar.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            const version = ++searchVersion;
            const query = this.value;
            const searchUrl = searchBar.dataset.searchUrl || '';
            searchTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    });
                    if (!response.ok) throw new Error('Search request failed');
                    const data = await response.json();
                    if (version !== searchVersion) return;
                    const tbody = document.getElementById('inventory-table-body');
                    if (tbody && Array.isArray(data.assets)) {
                        renderSearchResults(tbody, data.assets, query);
                    }
                } catch (error) {
                    console.error('Unable to search inventory:', error);
                }
            }, 300);
        });
    }

    // 5. Accountability Form Generator / Download Logic
    document.addEventListener("click", function (e) {
        const downloadBtn = e.target.closest(".download-accountability-btn");
        if (!downloadBtn) return;

        const assignedTo = downloadBtn.getAttribute("data-assignee");
        const targetUrl = downloadBtn.getAttribute("data-url");
        
        if (!assignedTo || !targetUrl) {
            alert("Missing assignee or download URL.");
            return;
        }

        // Create dynamic POST form to send the assignee to your views.py function
        const form = document.createElement("form");
        form.method = "POST";
        form.action = targetUrl;

        // Add CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            const csrfInput = document.createElement("input");
            csrfInput.type = "hidden";
            csrfInput.name = "csrfmiddlewaretoken";
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
        }

        // Add assigned_to field matching your backend expectation
        const userInput = document.createElement("input");
        userInput.type = "hidden";
        userInput.name = "assigned_to";
        userInput.value = assignedTo;
        form.appendChild(userInput);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    });

    // 6. Handle AJAX Form Submission to update inline without full page reloads
    const sharedUploadModal = document.getElementById('sharedUploadModal');
    if (sharedUploadModal) {
        sharedUploadModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (button) {
                const assignee = button.getAttribute('data-assignee');
                const uploadUrl = button.getAttribute('data-upload-url');
                
                const assigneeInput = document.getElementById('modalAssigneeInput');
                if (assigneeInput) assigneeInput.value = assignee;
                
                const uploadForm = document.getElementById('sharedUploadForm');
                if (uploadForm && uploadUrl) uploadForm.action = uploadUrl;
            }
        });
    }

    // 2. Handle AJAX Form Submission
    const uploadForm = document.getElementById('sharedUploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            e.preventDefault();
            
            const formData = new FormData(uploadForm);
            const actionUrl = uploadForm.action;
            
            let assigneeName = document.getElementById('modalAssigneeInput')?.value;
            if (!assigneeName) {
                assigneeName = formData.get('assignee');
            }
            
            fetch(actionUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    return response.json();
                } else {
                    return response.text().then(text => {
                        throw new Error("Server returned non-JSON response: " + text.substring(0, 100));
                    });
                }
            })
            .then(data => {
                if (data.status === 'success') {
                    // Remove focus to prevent aria-hidden warnings
                    if (document.activeElement && typeof document.activeElement.blur === 'function') {
                        document.activeElement.blur();
                    }

                    // Hide the upload modal cleanly
                    const uploadModalEl = document.getElementById('sharedUploadModal');
                    const uploadModalBs = bootstrap.Modal.getInstance(uploadModalEl);
                    if (uploadModalBs) {
                        uploadModalBs.hide();
                    }
                    
                    // Instantly update the table cell using the data-assignee attribute
                    if (assigneeName && data.scan_url) {
                        const escapedName = assigneeName.replace(/"/g, '\\"');
                        const scanCell = document.querySelector(`.scan-cell[data-assignee="${escapedName}"]`);
                        
                        if (scanCell) {
                            scanCell.innerHTML = `
                                <a href="${data.scan_url}" target="_blank" class="btn btn-sm btn-outline-success" title="View Signed Form">
                                    <i class="bi bi-file-earmark-check me-1"></i> View Scan
                                </a>
                            `;
                        }
                    }
                    
                    uploadForm.reset();

                    // Ensure the Manage Accountability modal remains active/visible
                    const manageModalEl = document.getElementById('manageAccountabilityModal');
                    if (manageModalEl) {
                        const manageModalBs = bootstrap.Modal.getInstance(manageModalEl) || new bootstrap.Modal(manageModalEl);
                        manageModalBs.show();
                    }
                } else {
                    alert('Upload failed: ' + (data.message || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred during file upload. Check the browser console for details.');
            });
        });
    }

    // 8. Editing the Username, Password, Email and Full Name
    const editUserModal = document.getElementById('editUserModal');
    if (editUserModal) {
        editUserModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            
            // Extract info from data-* attributes
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            const firstName = button.getAttribute('data-first-name');
            const lastName = button.getAttribute('data-last-name');
            const email = button.getAttribute('data-email');
            const role = button.getAttribute('data-role');
            
            // Populate modal inputs, filtering out Python's 'None' string
            editUserModal.querySelector('#modalUserId').value = userId;
            editUserModal.querySelector('#modalUsernameInput').value = username;
            editUserModal.querySelector('#modalUsernameDisplay').textContent = username;
            
            editUserModal.querySelector('#modalFirstNameInput').value = (firstName && firstName !== 'None') ? firstName : '';
            editUserModal.querySelector('#modalLastNameInput').value = (lastName && lastName !== 'None') ? lastName : '';
            editUserModal.querySelector('#modalEmailInput').value = (email && email !== 'None') ? email : '';
            
            // Set the role select dropdown
            const roleSelect = editUserModal.querySelector('#modalRoleSelect');
            if (role && role !== 'None') {
                roleSelect.value = role;
            } else {
                roleSelect.selectedIndex = 0;
            }
            
            // Clear password field on open
            editUserModal.querySelector('#modalPasswordInput').value = '';
        });
    }
});

