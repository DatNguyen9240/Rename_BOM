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
    const btnStop = document.getElementById('btnStop');
    const btnCopyBom = document.getElementById('btnCopyBom');
    const btnDownloadZip = document.getElementById('btnDownloadZip');
    const btnClear = document.getElementById('btnClear');

    let isStopRequested = false;

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
                <td style="color: #94a3b8;">${escapeHtml(file.name)}</td>
                <td style="text-align: center;"><span class="badge badge-gray"><i class="fa-solid fa-hourglass-start"></i> Sẵn sàng</span></td>
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

            const tag = r.bom_type.includes('2') ? 'BOM2' : 'BOM1';
            const codeWithBom = r.code && r.code !== '---' ? `${r.code}(${tag})` : '---';

            tr.innerHTML = `
                <td style="color: #64748b; text-align: center;">${index + 1}</td>
                <td>${escapeHtml(r.original_name)}</td>
                <td class="monospace" style="color: #38bdf8; font-weight: 700;">${escapeHtml(codeWithBom)}</td>
                <td class="monospace" style="color: #34d399; font-weight: 600;">${escapeHtml(r.new_filename)}</td>
                <td style="text-align: center;">${statusBadge}</td>
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

    // --- AI OCR Batch Scanning Execution (Real-time stream per file) ---
    btnScan.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        isStopRequested = false;
        btnScan.disabled = true;
        btnStop.disabled = false;
        btnClear.disabled = true;
        btnCopyBom.disabled = true;
        btnDownloadZip.disabled = true;
        if (btnQuickCopy) btnQuickCopy.disabled = true;

        progressWrapper.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressPercent.innerText = '0%';

        scanResults = [];
        let bom1Count = 0;
        let bom2Count = 0;
        let successCount = 0;
        let clientSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
        currentSessionId = clientSessionId;

        const totalFiles = selectedFiles.length;

        for (let i = 0; i < totalFiles; i++) {
            if (isStopRequested) {
                progressStatus.innerHTML = `<span style="color: #fbbf24;"><i class="fa-solid fa-circle-pause"></i> Đã dừng quét theo yêu cầu (${i}/${totalFiles} tệp).</span>`;
                break;
            }

            const file = selectedFiles[i];
            const fileNum = i + 1;

            // Update UI status for current file
            const currentRatio = Math.round((i / totalFiles) * 100);
            progressBar.style.width = `${currentRatio}%`;
            progressPercent.innerText = `${currentRatio}%`;
            progressStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang quét (${fileNum}/${totalFiles}): <strong>${escapeHtml(file.name)}</strong>...`;

            // Mark row as processing in table
            const row = tableBody.children[i];
            if (row) {
                const statusCell = row.cells[4];
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge badge-blue"><i class="fa-solid fa-spinner fa-spin"></i> Đang quét...</span>`;
                }
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', clientSessionId);
            formData.append('regex_pattern', txtRegex.value.trim());
            formData.append('min_length', txtMinLen.value);
            formData.append('max_length', txtMaxLen.value);

            try {
                const response = await fetch('/api/scan-single', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error('Lỗi máy chủ khi quét file');
                }

                const res = await response.json();
                if (res.session_id) currentSessionId = res.session_id;
                scanResults.push(res);

                // Update row in table immediately
                if (row) {
                    let statusBadge = '';
                    if (res.status === 'Nhận diện thành công') {
                        statusBadge = `<span class="badge badge-green"><i class="fa-solid fa-circle-check"></i> Thành công</span>`;
                    } else {
                        statusBadge = `<span class="badge badge-red"><i class="fa-solid fa-circle-xmark"></i> ${escapeHtml(res.status)}</span>`;
                    }

                    const tag = res.bom_type.includes('2') ? 'BOM2' : 'BOM1';
                    const codeWithBom = res.code && res.code !== '---' ? `${res.code}(${tag})` : '---';

                    row.cells[2].innerText = codeWithBom;
                    row.cells[2].style.color = '#38bdf8';
                    row.cells[2].style.fontWeight = '700';

                    row.cells[3].innerText = res.new_filename;
                    row.cells[3].style.color = '#34d399';
                    row.cells[3].style.fontWeight = '600';

                    row.cells[4].innerHTML = statusBadge;
                }

                if (res.code && res.code !== '---') {
                    successCount++;
                    if (res.bom_type.includes('2')) bom2Count++;
                    else bom1Count++;
                }

            } catch (err) {
                console.error(`Error scanning ${file.name}:`, err);
                scanResults.push({
                    original_name: file.name,
                    code: '---',
                    bom_type: 'Không rõ',
                    new_filename: file.name,
                    confidence: 0,
                    status: 'Lỗi xử lý',
                });
                if (row && row.cells[4]) {
                    row.cells[4].innerHTML = `<span class="badge badge-red"><i class="fa-solid fa-triangle-exclamation"></i> Lỗi xử lý</span>`;
                }
            }

            // Update stats badge and progress after each file
            updateStats(totalFiles, bom1Count, bom2Count, successCount);
            const finishedRatio = Math.round(((i + 1) / totalFiles) * 100);
            progressBar.style.width = `${finishedRatio}%`;
            progressPercent.innerText = `${finishedRatio}%`;
        }

        // Processing finished (either 100% or stopped)
        btnStop.disabled = true;
        btnScan.disabled = false;
        btnClear.disabled = false;

        if (!isStopRequested) {
            progressBar.style.width = '100%';
            progressPercent.innerText = '100%';
            progressStatus.innerHTML = `✅ Quét OCR hoàn tất! Nhận diện thành công ${successCount}/${totalFiles} tệp.`;
        }

        // Generate clean BOM code string for all scanned items
        const cleanCodes = scanResults
            .filter(r => r.code && r.code !== '---')
            .map(r => {
                const tag = r.bom_type.includes('2') ? 'BOM2' : 'BOM1';
                return `${r.code}(${tag})`;
            });

        const quickBox = document.getElementById('quickResultBox');
        const quickText = document.getElementById('quickResultText');

        if (quickBox && quickText && cleanCodes.length > 0) {
            quickText.value = cleanCodes.join(', ');
            quickBox.classList.remove('hidden');
        }

        if (cleanCodes.length > 0) {
            if (btnQuickCopy) btnQuickCopy.disabled = false;
            btnCopyBom.disabled = false;
            btnDownloadZip.disabled = false;
        }
    });

    // --- Stop Button Handler ---
    if (btnStop) {
        btnStop.addEventListener('click', () => {
            isStopRequested = true;
            btnStop.disabled = true;
            progressStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang dừng tiến trình quét...`;
        });
    }

    // --- Direct Quick Copy Handlers ---
    const btnQuickCopy = document.getElementById('btnQuickCopy');
    const btnCopyQuickResult = document.getElementById('btnCopyQuickResult');
    const quickText = document.getElementById('quickResultText');

    function performQuickCopy(btnElement) {
        if (!quickText || !quickText.value.trim()) return;
        navigator.clipboard.writeText(quickText.value.trim()).then(() => {
            const originalHTML = btnElement.innerHTML;
            btnElement.innerHTML = `<i class="fa-solid fa-check"></i> ✅ Đã Copy Mã!`;
            setTimeout(() => {
                btnElement.innerHTML = originalHTML;
            }, 2500);
        }).catch(() => {
            quickText.select();
            document.execCommand('copy');
            alert('Đã copy chuỗi mã vào bộ nhớ tạm!');
        });
    }

    if (btnQuickCopy) {
        btnQuickCopy.addEventListener('click', () => performQuickCopy(btnQuickCopy));
    }
    if (btnCopyQuickResult) {
        btnCopyQuickResult.addEventListener('click', () => performQuickCopy(btnCopyQuickResult));
    }

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
        const quickBox = document.getElementById('quickResultBox');
        if (quickBox) quickBox.classList.add('hidden');
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

        const btnQuickCopy = document.getElementById('btnQuickCopy');
        if (btnQuickCopy) btnQuickCopy.disabled = true;
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

    const chkUniqueOnly = document.getElementById('chkUniqueOnly');

    selModalFormat.addEventListener('change', updateModalPreview);
    selModalDelim.addEventListener('change', updateModalPreview);
    if (chkUniqueOnly) {
        chkUniqueOnly.addEventListener('change', updateModalPreview);
    }

    function updateModalPreview() {
        const fmt = selModalFormat.value;
        const delimChoice = selModalDelim.value;
        const isUniqueOnly = chkUniqueOnly ? chkUniqueOnly.checked : false;

        let validResults = scanResults.filter(r => r.code && r.code !== '---');

        if (activeModalFilter === 'bom1') {
            validResults = validResults.filter(r => r.bom_type.includes('1') || (r.bom_type.includes('BOM') && !r.bom_type.includes('2')));
        } else if (activeModalFilter === 'bom2') {
            validResults = validResults.filter(r => r.bom_type.includes('2'));
        }

        const seenItems = new Set();
        const formatted = [];

        validResults.forEach(r => {
            const tag = r.bom_type.includes('2') ? 'BOM2' : 'BOM1';
            let itemStr = '';

            if (fmt === 'code_tag_compact') {
                itemStr = `${r.code}(${tag})`;
            } else if (fmt === 'code_tag_space') {
                itemStr = `${r.code} (${tag})`;
            } else if (fmt === 'code_only') {
                itemStr = r.code;
            } else {
                itemStr = `${r.original_name} -> ${r.code}(${tag})`;
            }

            if (isUniqueOnly) {
                if (!seenItems.has(itemStr)) {
                    seenItems.add(itemStr);
                    formatted.push(itemStr);
                }
            } else {
                formatted.push(itemStr);
            }
        });

        let separator = ', ';
        if (delimChoice === 'newline') separator = '\n';
        else if (delimChoice === 'semicolon') separator = '; ';

        txtModalOutput.value = formatted.join(separator);
        modalMsg.innerText = `Đã xuất ${formatted.length} mã.`;
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
