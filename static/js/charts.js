/**
 * Chart functions for Banking App Analyzer
 */

/**
 * Create a chart for app ratings comparison
 * @param {string} canvasId - The ID of the canvas element
 * @param {Array} appData - Array of app information objects
 */
function createRatingsChart(canvasId, appData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Extract data for the chart
    const labels = appData.map(app => app.title);
    const ratings = appData.map(app => app.score);
    const colors = generateColors(appData.length);
    
    // Create chart
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Rating',
                data: ratings,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Rating: ${context.parsed.y.toFixed(1)}/5.0`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 5,
                    title: {
                        display: true,
                        text: 'Rating (out of 5)'
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Create a chart for app downloads comparison
 * @param {string} canvasId - The ID of the canvas element
 * @param {Array} appData - Array of app information objects
 */
function createDownloadsChart(canvasId, appData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Extract data for the chart
    const labels = appData.map(app => app.title);
    const installs = appData.map(app => app.installs);
    const colors = generateColors(appData.length, 'blue');
    
    // Create chart
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Installs',
                data: installs,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Installs: ${context.parsed.y.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Installs'
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Generate color arrays for charts
 * @param {number} count - Number of colors to generate
 * @param {string} baseColor - Base color theme (optional)
 * @returns {Object} Object with background and border color arrays
 */
function generateColors(count, baseColor = 'multicolor') {
    const backgroundColors = [];
    const borderColors = [];
    
    if (baseColor === 'multicolor') {
        // Generate a variety of colors
        const baseColors = [
            [40, 167, 69],   // green 
            [0, 123, 255],   // blue
            [255, 193, 7],   // yellow
            [220, 53, 69],   // red
            [111, 66, 193],  // purple
            [23, 162, 184],  // cyan
            [253, 126, 20],  // orange
            [32, 201, 151]   // teal
        ];
        
        for (let i = 0; i < count; i++) {
            const colorIndex = i % baseColors.length;
            const [r, g, b] = baseColors[colorIndex];
            backgroundColors.push(`rgba(${r}, ${g}, ${b}, 0.8)`);
            borderColors.push(`rgba(${r}, ${g}, ${b}, 1)`);
        }
    } else if (baseColor === 'blue') {
        // Generate different shades of blue
        for (let i = 0; i < count; i++) {
            const shade = Math.floor(150 + (i * 80 / count)) % 255;
            backgroundColors.push(`rgba(0, ${shade}, 255, 0.8)`);
            borderColors.push(`rgba(0, ${shade}, 255, 1)`);
        }
    } else if (baseColor === 'green') {
        // Generate different shades of green
        for (let i = 0; i < count; i++) {
            const shade = Math.floor(100 + (i * 155 / count)) % 255;
            backgroundColors.push(`rgba(${Math.floor(40 + i*20/count)}, ${shade}, 40, 0.8)`);
            borderColors.push(`rgba(${Math.floor(40 + i*20/count)}, ${shade}, 40, 1)`);
        }
    } else {
        // Default to gray if base color not recognized
        for (let i = 0; i < count; i++) {
            const shade = Math.floor(100 + (i * 155 / count)) % 255;
            backgroundColors.push(`rgba(${shade}, ${shade}, ${shade}, 0.8)`);
            borderColors.push(`rgba(${shade}, ${shade}, ${shade}, 1)`);
        }
    }
    
    return {
        background: backgroundColors,
        border: borderColors
    };
}
