export async function telechargerDevisPDF(element, filename = 'devis.pdf') {
    if (!element || !window.html2canvas || !window.jspdf) {
        alert('Impossible de générer le PDF. Réessayez dans quelques secondes.');
        return;
    }

    const saved = {
        position: element.style.position,
        left: element.style.left,
        top: element.style.top,
        display: element.style.display,
        width: element.style.width,
        background: element.style.background,
        zIndex: element.style.zIndex,
    };

    element.style.position = 'fixed';
    element.style.left = '-10000px';
    element.style.top = '0';
    element.style.display = 'block';
    element.style.width = '794px';
    element.style.background = '#ffffff';
    element.style.zIndex = '-1';

    try {
        const canvas = await window.html2canvas(element, {
            scale: 2,
            backgroundColor: '#ffffff',
            useCORS: true,
            logging: false,
        });

        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        const pageWidth = 210;
        const pageHeight = 297;
        const margin = 10;
        const imgWidth = pageWidth - margin * 2;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        const imgData = canvas.toDataURL('image/png');

        if (imgHeight <= pageHeight - margin * 2) {
            pdf.addImage(imgData, 'PNG', margin, margin, imgWidth, imgHeight);
        } else {
            const usable = pageHeight - margin * 2;
            let remaining = imgHeight;
            let offset = 0;
            while (remaining > 0) {
                pdf.addImage(imgData, 'PNG', margin, margin - offset, imgWidth, imgHeight);
                remaining -= usable;
                offset += usable;
                if (remaining > 0) pdf.addPage();
            }
        }

        pdf.save(filename);
    } catch (e) {
        console.error(e);
        alert('Erreur lors de la génération du PDF.');
    } finally {
        Object.keys(saved).forEach((k) => {
            element.style[k] = saved[k];
        });
    }
}
