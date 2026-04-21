from weasyprint import HTML

html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: Arial;
            font-size: 12px;
        }

        header {
            position: running(header);
            text-align: center;
            font-weight: bold;
        }

        footer {
            position: running(footer);
            font-size: 10px;
            text-align: center;
        }

        @page {
            @top-center {
                content: element(header);
            }
            @bottom-center {
                content: element(footer);
            }
        }
    </style>
</head>
<body>

<header>
    Kheyrat Secondary School — Term Report
</header>

<footer>
    Page <span class="pageNumber"></span>
</footer>

<p>This page tests margins, header, and footer.</p>

</body>
</html>
"""

HTML(string=html).write_pdf("page_control.pdf")
