document.addEventListener('DOMContentLoaded', () => {
    function initCustomSelect(select) {
        if (select.dataset.customSelectInitialized) return;
        select.dataset.customSelectInitialized = 'true';
        select.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper position-relative';
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);

        const trigger = document.createElement('div');
        trigger.className = select.className.replace('form-select', 'form-control') + ' custom-select-trigger d-flex justify-content-between align-items-center';
        trigger.style.cursor = 'pointer';
        // Ensure trigger looks like pm-input
        if (!trigger.classList.contains('pm-input')) {
            trigger.classList.add('pm-input');
        }
        
        trigger.innerHTML = '<span></span><i class="bi bi-chevron-down ms-2 text-muted-custom"></i>';
        const textSpan = trigger.querySelector('span');
        
        const updateText = () => {
            const selectedOpt = select.options[select.selectedIndex];
            textSpan.textContent = selectedOpt ? selectedOpt.textContent : '';
        };
        updateText();
        
        const optionsList = document.createElement('div');
        optionsList.className = 'custom-select-options';
        optionsList.style.position = 'absolute';
        optionsList.style.top = '100%';
        optionsList.style.left = '0';
        optionsList.style.right = '0';
        optionsList.style.backgroundColor = 'var(--bg-card, #1c2331)';
        optionsList.style.border = '1px solid rgba(255,255,255,0.1)';
        optionsList.style.borderRadius = '10px';
        optionsList.style.marginTop = '4px';
        optionsList.style.zIndex = '1000';
        optionsList.style.display = 'none';
        optionsList.style.maxHeight = '250px';
        optionsList.style.overflowY = 'auto';
        optionsList.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';

        const buildOptions = () => {
            optionsList.innerHTML = '';
            Array.from(select.options).forEach((opt, index) => {
                const optionDiv = document.createElement('div');
                optionDiv.className = 'custom-select-option px-3 py-2';
                optionDiv.textContent = opt.textContent;
                optionDiv.style.cursor = 'pointer';
                optionDiv.style.color = '#fff';
                optionDiv.style.transition = 'background-color 0.1s';
                
                if (opt.selected) {
                    optionDiv.style.backgroundColor = '#8CE1B2';
                    optionDiv.style.color = '#121929';
                    optionDiv.style.fontWeight = 'bold';
                }

                optionDiv.addEventListener('mouseover', () => {
                    optionDiv.style.backgroundColor = '#8CE1B2';
                    optionDiv.style.color = '#121929';
                });
                optionDiv.addEventListener('mouseout', () => {
                    if (!opt.selected) {
                        optionDiv.style.backgroundColor = 'transparent';
                        optionDiv.style.color = '#fff';
                    }
                });

                optionDiv.addEventListener('click', (e) => {
                    e.stopPropagation();
                    select.selectedIndex = index;
                    select.dispatchEvent(new Event('change'));
                    updateText();
                    optionsList.style.display = 'none';
                    buildOptions();
                });
                optionsList.appendChild(optionDiv);
            });
        };

        wrapper.appendChild(trigger);
        wrapper.appendChild(optionsList);

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = optionsList.style.display === 'block';
            document.querySelectorAll('.custom-select-options').forEach(el => el.style.display = 'none');
            if (!isOpen) {
                buildOptions();
                optionsList.style.display = 'block';
            }
        });

        document.addEventListener('click', () => {
            optionsList.style.display = 'none';
        });

        const observer = new MutationObserver(() => {
            updateText();
            if (optionsList.style.display === 'block') {
                buildOptions();
            }
        });
        observer.observe(select, { childList: true });
        
        select.addEventListener('change', () => {
            const selectedOpt = select.options[select.selectedIndex];
            textSpan.textContent = selectedOpt ? selectedOpt.textContent : '';
        });
    }

    document.querySelectorAll('select.pm-input').forEach(initCustomSelect);
    
    // In case new selects are added to DOM later
    const bodyObserver = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1) {
                    if (node.matches && node.matches('select.pm-input')) {
                        initCustomSelect(node);
                    }
                    if (node.querySelectorAll) {
                        node.querySelectorAll('select.pm-input').forEach(initCustomSelect);
                    }
                }
            });
        });
    });
    bodyObserver.observe(document.body, { childList: true, subtree: true });
});
