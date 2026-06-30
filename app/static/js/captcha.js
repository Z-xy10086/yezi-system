function initCaptcha() {
    const captchaBg = document.getElementById('captcha-bg');
    const captchaSlider = document.getElementById('captcha-slider');
    const captchaTips = document.getElementById('captcha-tips');
    const submitBtn = document.getElementById('submit-btn');
    const captchaTokenInput = document.getElementById('captcha-token');
    
    let isDragging = false;
    let startX = 0;
    let currentX = 0;
    let token = '';
    let sliderWidth = 50;
    
    function loadCaptcha() {
        fetch('/captcha')
            .then(response => response.json())
            .then(data => {
                token = data.token;
                sliderWidth = data.slider_width || 50;
                
                captchaTokenInput.value = token;
                
                const bgBytes = hexToBytes(data.bg_image);
                const bgBlob = new Blob([bgBytes], { type: 'image/png' });
                const bgUrl = URL.createObjectURL(bgBlob);
                
                const sliderBytes = hexToBytes(data.slider_image);
                const sliderBlob = new Blob([sliderBytes], { type: 'image/png' });
                const sliderUrl = URL.createObjectURL(sliderBlob);
                
                captchaBg.innerHTML = `<img src="${bgUrl}" alt="captcha">`;
                captchaSlider.innerHTML = '<div class="slider-arrow"></div>';
                
                captchaSlider.style.width = sliderWidth + 'px';
                captchaSlider.style.height = sliderWidth + 'px';
                captchaSlider.style.top = '50%';
                captchaSlider.style.transform = 'translateY(-50%)';
                
                captchaTips.textContent = '请拖动滑块完成验证';
                captchaTips.style.color = '#6c757d';
                submitBtn.disabled = true;
                captchaSlider.style.left = '0';
            })
            .catch(error => {
                console.error('加载验证码失败:', error);
                captchaTips.textContent = '验证码加载失败，请刷新页面';
                captchaTips.style.color = '#dc3545';
            });
    }
    
    function hexToBytes(hex) {
        const bytes = [];
        for (let i = 0; i < hex.length; i += 2) {
            bytes.push(parseInt(hex.substr(i, 2), 16));
        }
        return new Uint8Array(bytes);
    }
    
    captchaSlider.addEventListener('mousedown', startDrag);
    captchaSlider.addEventListener('touchstart', startDrag, { passive: false });
    
    function startDrag(e) {
        isDragging = true;
        startX = (e.touches ? e.touches[0].clientX : e.clientX) - currentX;
        captchaSlider.classList.add('dragging');
        
        document.addEventListener('mousemove', onDrag);
        document.addEventListener('touchmove', onDrag, { passive: false });
        document.addEventListener('mouseup', stopDrag);
        document.addEventListener('touchend', stopDrag);
    }
    
    function onDrag(e) {
        if (!isDragging) return;
        
        e.preventDefault();
        
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        let newX = clientX - startX;
        
        const maxX = captchaBg.offsetWidth - sliderWidth;
        
        if (newX < 0) newX = 0;
        if (newX > maxX) newX = maxX;
        
        currentX = newX;
        captchaSlider.style.left = currentX + 'px';
    }
    
    function stopDrag() {
        if (!isDragging) return;
        
        isDragging = false;
        captchaSlider.classList.remove('dragging');
        
        document.removeEventListener('mousemove', onDrag);
        document.removeEventListener('touchmove', onDrag);
        document.removeEventListener('mouseup', stopDrag);
        document.removeEventListener('touchend', stopDrag);
        
        verifyCaptcha(currentX);
    }
    
    function verifyCaptcha(sliderX) {
        captchaTips.textContent = '验证中...';
        captchaTips.style.color = '#17a2b8';
        
        fetch('/captcha/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token: token,
                slider_x: sliderX
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                captchaTips.textContent = '验证成功';
                captchaTips.style.color = '#28a745';
                submitBtn.disabled = false;
            } else {
                captchaTips.textContent = data.message || '验证失败，请重新尝试';
                captchaTips.style.color = '#dc3545';
                
                setTimeout(() => {
                    captchaSlider.style.left = '0';
                    currentX = 0;
                    loadCaptcha();
                }, 500);
            }
        })
        .catch(error => {
            console.error('验证失败:', error);
            captchaTips.textContent = '验证失败，请刷新页面';
            captchaTips.style.color = '#dc3545';
        });
    }
    
    loadCaptcha();
}