import os
import jinja2
import subprocess
import tempfile
import shutil

import re

class LatexSurgeon:
    def __init__(self, template_dir: str):
        self.template_dir = template_dir
        # Configure Jinja2 for LaTeX (avoiding brace conflicts)
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            block_start_string='((*',
            block_end_string='*))',
            variable_start_string='((',
            variable_end_string='))',
            comment_start_string='((#',
            comment_end_string='#))',
            trim_blocks=True,
            lstrip_blocks=True
        )

    def escape_latex_special_chars(self, data):
        """
        Recursively escapes special LaTeX characters in the data.
        Also converts Markdown bold (**text**) to LaTeX bold (\textbf{text}).
        """
        if isinstance(data, str):
            escape_chars = {
                '&': r'\&',
                '%': r'\%',
                '$': r'\$',
                '#': r'\#',
                '_': r'\_',
                '{': r'\{',
                '}': r'\}',
                '~': r'\textasciitilde{}',
                '^': r'\textasciicircum{}',
                '\\': r'\textbackslash{}',
            }
            # 1. Escape special characters
            escaped_str = "".join(escape_chars.get(c, c) for c in data)
            
            # 2. Convert Markdown bold (**text**) to LaTeX (\textbf{text})
            # We match **content** non-greedily
            final_str = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', escaped_str)
            
            return final_str
        elif isinstance(data, dict):
            return {k: self.escape_latex_special_chars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.escape_latex_special_chars(v) for v in data]
        return data

    def fill_template(self, template_name: str, data: dict) -> str:
        """
        Renders the LaTeX template with the provided data.
        Returns the rendered LaTeX string.
        """
        try:
            # Sanitize data to prevent LaTeX compilation errors
            safe_data = self.escape_latex_special_chars(data)
            
            template = self.env.get_template(template_name)
            return template.render(**safe_data)
        except Exception as e:
            print(f"❌ [LatexSurgeon] Template Rendering Failed: {e}")
            raise e

    def compile_pdf(self, tex_content: str, output_filename: str = "output.pdf") -> str:
        """
        Compiles the LaTeX content to PDF using pdflatex.
        Returns the path to the generated PDF.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_path = os.path.join(temp_dir, "resume.tex")
            
            # Write .tex file
            with open(tex_path, "w") as f:
                f.write(tex_content)
                
            print(f"⚙️ [LatexSurgeon] Compiling PDF...")
            
            # Run pdflatex twice (for references/formatting)
            # We need to ensure we are in the temp_dir so aux files are generated there
            try:
                # 1st Run
                cmd = ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_path]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # 2nd Run (Optional but good for layout)
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                pdf_name = "resume.pdf"
                generated_pdf = os.path.join(temp_dir, pdf_name)
                
                if os.path.exists(generated_pdf):
                    # Move to a persistent location (or return temp path? Caller should handle)
                    # For safety, let's copy to a known temp location that persists after this context exits
                    final_path = os.path.join(tempfile.gettempdir(), output_filename)
                    shutil.copy(generated_pdf, final_path)
                    print(f"✅ [LatexSurgeon] PDF Compiled: {final_path}")
                    return final_path
                else:
                    print("❌ [LatexSurgeon] PDF file was not created by pdflatex.")
                    return None
                    
            except subprocess.CalledProcessError as e:
                print(f"❌ [LatexSurgeon] pdflatex failed: {e.stdout.decode()}\n{e.stderr.decode()}")
                return None
            except Exception as e:
                print(f"❌ [LatexSurgeon] Compilation Error: {e}")
                return None
