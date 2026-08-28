/**
 * AI OCR Rename BOM - Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let selectedFiles = [];
    let currentSessionId = null;
    let scanResults = [];

    // DOM Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const selPreset = document.getElementById('selPreset');
    const txtRegex = document.getElementById('txtRegex');
    const txtMinLen = document.getElementById('txtMinLen');
    const txtMaxLen = document.getElementById('txtMaxLen');

    const badgeTotal = document.getElementById('badgeTotal');
    const badgeBom1 = document.getElementById('badgeBom1');
    const badgeBom2 = document.getElementById('badgeBom2');
    const badgeSuccess = document.getElementById('badgeSuccess');

    const btnScan = document.getElementById('btnScan');
    const btnCopyBom = document.getElementById('btnCopyBom');
    const btnDownloadZip = document.getElementById('btnDownloadZip');
    const btnClear = document.getElementById('btnClear');

    const progressWrapper = document.getElementById('progressWrapper');
    const progressBar = document.getElementById('progressBar');
    const progressStatus = document.getElementById('progressStatus');
    const progressPercent = document.getElementById('progressPercent');

    const tableBody = document.getElementById('tableBody');

    // Modal Elements
    const copyModal = document.getElementById('copyModal');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const filterPills = document.getElementById('filterPills');
    const selModalFormat = document.getElementById('selModalFormat');
    const selModalDelim = document.getElementById('selModalDelim');
    const txtModalOutput = document.getElementById('txtModalOutput');
    const btnModalCopy = document.getElementById('btnModalCopy');
    const modalMsg = document.getElementById('modalMsg');

    let activeModalFilter = 'all';

    // --- Dropzone & File Selection ---
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFilesSelected(Array.from(e.dataTransfer.files));
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFilesSelected(Array.from(e.target.files));
        }
    });

    function handleFilesSelected(files) {
        const validExtensions = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'];
        const filtered = files.filter(f => {
            const ext = '.' + f.name.split('.').pop().toLowerCase();
            return validExtensions.includes(ext);
        });

        if (filtered.length === 0) {
            alert('Không tìm thấy tệp hợp lệ (.PDF, .JPG, .PNG, .WEBP).');
            return;
        }

        selectedFiles = filtered;
        scanResults = [];
        currentSessionId = null;

        updateStats(selectedFiles.length, 0, 0, 0);
        renderInitialTable(selectedFiles);

        btnScan.disabled = false;
        btnClear.disabled = false;
        btnCopyBom.disabled = true;
        btnDownloadZip.disabled = true;
    }

    // --- Preset Selection ---
    selPreset.addEventListener('change', () => {
        const choice = selPreset.value;
        if (choice === 'chenkai') {
            txtRegex.value = '[0-9A-Za-z]{6,15}-[0-9]{2}';
            txtMinLen.value = '8';
            txtMaxLen.value = '25';
        } else if (choice === 'bom') {
            txtRegex.value = '[0-9A-Za-z]{4,15}(?:-[0-9A-Za-z]+)?';
            txtMinLen.value = '6';
            txtMaxLen.value = '25';
        } else if (choice === 'customer') {
            txtRegex.value = '\\b\\d{8,12}\\b';
            txtMinLen.value = '8';
            txtMaxLen.value = '12';
        } else if (choice === 'alphanumeric') {
            txtRegex.value = '[A-Za-z0-9]{4,25}';
            txtMinLen.value = '4';
            txtMaxLen.value = '25';
        }
    });

    // --- Table Rendering ---
    function renderInitialTable(files) {
        tableBody.innerHTML = '';
        files.forEach((file, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color: #64748b; text-align: center;">${index + 1}</td>
                <td><strong>${escapeHtml(file.name)}</strong></td>
                <td style="color: #94a3b8;">---</td>
                <td style="text-align: center;"><span class="tag">-</span></td>
                <td style="color: #94a3b8;">${escapeHtml(file.name)}</td>
                <td style="text-align: center;">-</td>
                <td><span class="badge badge-gray"><i class="fa-solid fa-hourglass-start"></i> Sẵn sàng</span></td>
            `;
            tableBody.appendChild(tr);
        });
    }

    function renderResultsTable(results) {
        tableBody.innerHTML = '';
        results.forEach((r, index) => {
            const tr = document.createElement('tr');
            
            let statusBadge = '';
            if (r.status === 'Nhận diện thành công') {
                statusBadge = `<span class="badge badge-green"><i class="fa-solid fa-circle-check"></i> Thành công</span>`;
            } else {
                statusBadge = `<span class="badge badge-red"><i class="fa-solid fa-circle-xmark"></i> ${escapeHtml(r.status)}</span>`;
            }

            let bomBadge = '-';
            if (r.bom_type.includes('2')) {
                bomBadge = `<span class="badge badge-purple">BOM 2</span>`;
            } else if (r.bom_type.includes('1') || r.bom_type.includes('BOM')) {
                bomBadge = `<span class="badge badge-blue">BOM 1</span>`;
            }

            const confColor = r.confidence >= 90 ? '#34d399' : (r.confidence >= 70 ? '#fbbf24' : '#94a3b8');

            tr.innerHTML = `
                <td style="color: #64748b; text-align: center;">${index + 1}</td>
                <td>${escapeHtml(r.original_name)}</td>
                <td class="monospace" style="color: #38bdf8; font-weight: 700;">${escapeHtml(r.code)}</td>
                <td style="text-align: center;">${bomBadge}</td>
                <td class="monospace" style="color: #34d399; font-weight: 600;">${escapeHtml(r.new_filename)}</td>
                <td style="text-align: center; color: ${confColor}; font-weight: 600;">${r.confidence > 0 ? r.confidence + '%' : '-'}</td>
                <td>${statusBadge}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    function updateStats(total, bom1, bom2, success) {
        badgeTotal.innerHTML = `<i class="fa-solid fa-list"></i> Đã nạp: ${total}`;
        badgeBom1.innerHTML = `<i class="fa-solid fa-tag"></i> BOM 1: ${bom1}`;
        badgeBom2.innerHTML = `<i class="fa-solid fa-tags"></i> BOM 2: ${bom2}`;
        badgeSuccess.innerHTML = `<i class="fa-solid fa-check"></i> Nhận diện: ${success}`;
    }

    // --- AI OCR Batch Scanning Execution ---
    btnScan.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        btnScan.disabled = true;
        btnClear.disabled = true;
        btnCopyBom.disabled = true;
        btnDownloadZip.disabled = true;

        progressWrapper.classList.remove('hidden');
        progressBar.style.width = '10%';
        progressPercent.innerText = '10%';
        progressStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang tải lên và phân tích OCR (${selectedFiles.length} tệp)...`;

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('regex_pattern', txtRegex.value.trim());
        formData.append('min_length', txtMinLen.value);
        formData.append('max_length', txtMaxLen.value);

        try {
            progressBar.style.width = '45%';
            progressPercent.innerText = '45%';

            const response = await fetch('/api/scan', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || 'Lỗi xử lý OCR từ máy chủ.');
            }

            const data = await response.json();
            currentSessionId = data.session_id;
            scanResults = data.results;

            progressBar.style.width = '100%';
            progressPercent.innerText = '100%';
            progressStatus.innerHTML = `✅ Quét OCR hoàn tất thành công!`;

            // Calculate stats
            let bom1Count = 0;
            let bom2Count = 0;
            let successCount = 0;

            scanResults.forEach(r => {
                if (r.code && r.code !== '---') {
                    successCount++;
                    if (r.bom_type.includes('2')) bom2Count++;
                    else bom1Count++;
                }
            });

            updateStats(scanResults.length, bom1Count, bom2Count, successCount);
            renderResultsTable(scanResults);

            btnCopyBom.disabled = false;
            btnDownloadZip.disabled = false;
            btnClear.disabled = false;

        } catch (error) {
            console.error(error);
            alert(`Lỗi: ${error.message}`);
            progressStatus.innerHTML = `<span style="color: #ef4444;">❌ Lỗi: ${error.message}</span>`;
            btnClear.disabled = false;
            btnScan.disabled = false;
        }
    });

    // --- ZIP Download ---
    btnDownloadZip.addEventListener('click', () => {
        if (!currentSessionId) return;
        window.location.href = `/api/download-zip/${currentSessionId}`;
    });

    // --- Clear All ---
    btnClear.addEventListener('click', () => {
        selectedFiles = [];
        scanResults = [];
        currentSessionId = null;
        fileInput.value = '';

        updateStats(0, 0, 0, 0);
        progressWrapper.classList.add('hidden');
        progressBar.style.width = '0%';
        progressPercent.innerText = '0%';

        tableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="7">
                    <div class="empty-state">
                        <i class="fa-regular fa-folder-open"></i>
                        <p>Chưa có tệp nào. Vui lòng kéo thả hoặc chọn tệp bên trên.</p>
                    </div>
                </td>
            </tr>
        `;

        btnScan.disabled = true;
        btnCopyBom.disabled = true;
        btnDownloadZip.disabled = true;
        btnClear.disabled = true;
    });

    // --- Copy BOM Modal Logic ---
    btnCopyBom.addEventListener('click', () => {
        if (!scanResults || scanResults.length === 0) return;
        copyModal.classList.remove('hidden');
        updateModalPreview();
    });

    btnCloseModal.addEventListener('click', () => copyModal.classList.add('hidden'));

    filterPills.addEventListener('click', (e) => {
        if (e.target.classList.contains('pill-btn')) {
            filterPills.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            activeModalFilter = e.target.dataset.filter;
            updateModalPreview();
        }
    });

    selModalFormat.addEventListener('change', updateModalPreview);
    selModalDelim.addEventListener('change', updateModalPreview);

    function updateModalPreview() {
        const fmt = selModalFormat.value;
        const delimChoice = selModalDelim.value;

        let validResults = scanResults.filter(r => r.code && r.code !== '---');

        if (activeModalFilter === 'bom1') {
            validResults = validResults.filter(r => r.bom_type.includes('1') || r.bom_type.includes('BOM') && !r.bom_type.includes('2'));
        } else if (activeModalFilter === 'bom2') {
            validResults = validResults.filter(r => r.bom_type.includes('2'));
        }

        const formatted = validResults.map(r => {
            const tag = r.bom_type.includes('2') ? 'BOM2' : 'BOM1';
            if (fmt === 'code_tag') {
                return `${r.code} (${tag})`;
            } else if (fmt === 'code_only') {
                return r.code;
            } else {
                return `${r.original_name} -> ${r.code} (${tag})`;
            }
        });

        let separator = ', ';
        if (delimChoice === 'newline') separator = '\n';
        else if (delimChoice === 'semicolon') separator = '; ';

        txtModalOutput.value = formatted.join(separator);
        modalMsg.innerText = `Đã lọc ${formatted.length} mục.`;
    }

    btnModalCopy.addEventListener('click', () => {
        const text = txtModalOutput.value;
        if (!text.trim()) return;

        navigator.clipboard.writeText(text).then(() => {
            modalMsg.innerText = '✅ Đã sao chép vào Clipboard!';
            setTimeout(() => { modalMsg.innerText = ''; }, 3000);
        }).catch(err => {
            console.error('Clipboard error:', err);
            txtModalOutput.select();
            document.execCommand('copy');
            modalMsg.innerText = '✅ Đã sao chép vào Clipboard!';
        });
    });

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#039;');
    }
});
