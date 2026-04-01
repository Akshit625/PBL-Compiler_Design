document.getElementById('optimize-btn').addEventListener('click', async () => {
    const code = document.getElementById('input-code').value;
    console.log('Sending code:', code);
    try {
        const response = await fetch('/optimize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code })
        });
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Result:', result);
        if (result.success) {
            document.getElementById('output-code').textContent = result.optimized;
            alert('Optimization successful! Check the output area.');
        } else {
            document.getElementById('output-code').textContent = 'Error: ' + result.error;
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.log('Fetch error:', error);
        document.getElementById('output-code').textContent = 'Error: ' + error.message;
        alert('Fetch error: ' + error.message);
    }
});