"""
Email module for sending notifications about new URLs.
"""
import smtplib
import logging
import csv
from io import StringIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Dict
from datetime import datetime


class EmailSender:
    """Sends email notifications via SMTP."""

    BODY_URL_LIMIT_PER_SOURCE = 100
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        logger: logging.Logger
    ):
        """
        Initialize email sender.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_email: From email address
            logger: Logger instance
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.logger = logger
    
    def _create_urls_attachment_content(self, new_urls_by_source: Dict[str, List[str]]) -> str:
        """
        Create CSV content containing all discovered URLs.

        Args:
            new_urls_by_source: Dictionary mapping source names to lists of URLs

        Returns:
            CSV string with all URLs
        """
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["source", "url"])

        for source_name, urls in new_urls_by_source.items():
            for url in urls:
                writer.writerow([source_name, url])

        return output.getvalue()

    def _create_html_content(self, new_urls_by_source: Dict[str, List[str]], total_new: int) -> str:
        """
        Create HTML email content.
        
        Args:
            new_urls_by_source: Dictionary mapping source names to lists of URLs
            total_new: Total number of new URLs
            
        Returns:
            HTML string
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }",
            "h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }",
            "h2 { color: #34495e; margin-top: 30px; }",
            ".summary { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }",
            ".url-list { margin: 10px 0; }",
            ".url-item { padding: 8px; margin: 5px 0; background-color: #f8f9fa; border-left: 3px solid #3498db; }",
            ".url-item a { color: #2980b9; text-decoration: none; word-break: break-all; }",
            ".url-item a:hover { text-decoration: underline; }",
            ".source-section { margin: 25px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }",
            ".timestamp { color: #7f8c8d; font-size: 0.9em; }",
            ".no-urls { color: #95a5a6; font-style: italic; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1> Daily General Web Scraping Links</h1>",
            f"<p class='timestamp'>Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<div class='summary'>",
            f"<strong>Summary:</strong> Found <strong>{total_new}</strong> new URL(s) today",
            "</div>"
        ]
        
        if total_new == 0:
            html_parts.append("<p class='no-urls'>No new URLs discovered today.</p>")
        else:
            for source_name, urls in new_urls_by_source.items():
                if urls:
                    html_parts.append("<div class='source-section'>")
                    html_parts.append(f"<h2>{source_name.replace('_', ' ').title()}</h2>")
                    html_parts.append(f"<p><strong>{len(urls)}</strong> new URL(s)</p>")
                    html_parts.append("<div class='url-list'>")
                    
                    display_urls = urls[:self.BODY_URL_LIMIT_PER_SOURCE]
                    remaining_count = len(urls) - len(display_urls)

                    for url in display_urls:
                        html_parts.append(f"<div class='url-item'>")
                        html_parts.append(f"<a href='{url}' target='_blank'>{url}</a>")
                        html_parts.append("</div>")

                    if remaining_count > 0:
                        html_parts.append(
                            f"<p class='no-urls'>Showing first {len(display_urls)} URLs. "
                            f"See attached CSV for remaining {remaining_count} URL(s).</p>"
                        )
                    
                    html_parts.append("</div>")
                    html_parts.append("</div>")
        
        html_parts.extend([
            "<hr>",
            "<p style='color: #7f8c8d; font-size: 0.85em;'>",
            "This is an automated email from your daily URL scraper.",
            "</p>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    def _create_text_content(self, new_urls_by_source: Dict[str, List[str]], total_new: int) -> str:
        """
        Create plain text email content.
        
        Args:
            new_urls_by_source: Dictionary mapping source names to lists of URLs
            total_new: Total number of new URLs
            
        Returns:
            Plain text string
        """
        lines = [
            "="*70,
            "Daily General Web Scraping Links",
            "="*70,
            f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Summary: Found {total_new} new URL(s) today",
            "="*70,
            ""
        ]
        
        if total_new == 0:
            lines.append("No new URLs discovered today.")
        else:
            for source_name, urls in new_urls_by_source.items():
                if urls:
                    lines.append(f"\n{source_name.replace('_', ' ').upper()}")
                    lines.append("-" * 70)
                    lines.append(f"Found {len(urls)} new URL(s):")
                    lines.append("")
                    
                    display_urls = urls[:self.BODY_URL_LIMIT_PER_SOURCE]
                    remaining_count = len(urls) - len(display_urls)

                    for i, url in enumerate(display_urls, 1):
                        lines.append(f"{i}. {url}")

                    if remaining_count > 0:
                        lines.append(
                            f"Showing first {len(display_urls)} URLs. "
                            f"See attached CSV for remaining {remaining_count} URL(s)."
                        )
                    
                    lines.append("")
        
        lines.extend([
            "",
            "-"*70,
            "This is an automated email from your daily URL scraper."
        ])
        
        return "\n".join(lines)
    
    def send_report(self, to_emails: List[str], new_urls_by_source: Dict[str, List[str]]) -> bool:
        """
        Send email report with new URLs.

        Args:
            to_emails: List of recipient email addresses
            new_urls_by_source: Dictionary mapping source names to lists of new URLs

        Returns:
            True if email sent successfully, False otherwise
        """
        if not to_emails or not isinstance(to_emails, list):
            self.logger.error("No recipients provided (to_emails must be a non-empty list).")
            return False

        # Clean recipients (strip whitespace)
        to_emails = [e.strip() for e in to_emails if e and e.strip()]
        if not to_emails:
            self.logger.error("Recipient list is empty after cleaning.")
            return False

        total_new = sum(len(urls) for urls in new_urls_by_source.values())

        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = "Daily General Web Scraping Links"
            message['From'] = self.from_email
            message['To'] = ", ".join(to_emails)
            message['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

            text_content = self._create_text_content(new_urls_by_source, total_new)
            html_content = self._create_html_content(new_urls_by_source, total_new)

            message.attach(MIMEText(text_content, 'plain'))
            message.attach(MIMEText(html_content, 'html'))

            # Attach the complete URL list so no scraped data is dropped.
            attachment_content = self._create_urls_attachment_content(new_urls_by_source)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            attachment = MIMEApplication(attachment_content.encode('utf-8'), _subtype='csv')
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=f"all_new_urls_{timestamp}.csv"
            )
            message.attach(attachment)

            self.logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()

                self.logger.info("Logging in to SMTP server")
                server.login(self.username, self.password)

                self.logger.info(f"Sending email to {', '.join(to_emails)}")
                server.send_message(message, to_addrs=to_emails)

            self.logger.info("Email sent successfully!")
            return True

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            self.logger.error(
                "Please check sender_email and sender_password in your active email config file."
            )
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending email: {e}", exc_info=True)
            return False
