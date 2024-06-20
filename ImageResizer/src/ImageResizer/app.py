import toga
from toga.style import Pack
from toga.style.pack import COLUMN
from PIL import Image
import webbrowser
import tempfile
import os

class ImageResizerApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title="Image Resizer")
        self.set_logo("logo.png")  # Path to your logo file

        self.file_path = None
        self.image = None

        self.create_widgets()
        self.main_window.show()

    def create_widgets(self):
        self.label = toga.Label("Select an image to resize:", style=Pack(padding=(0, 5)))
        self.open_button = toga.Button("Open Image", on_press=self.open_image, style=Pack(padding=(0, 5)))

        self.width_label = toga.Label("Width:", style=Pack(padding=(0, 5)))
        self.width_entry = toga.TextInput(style=Pack(flex=1))
        self.height_label = toga.Label("Height:", style=Pack(padding=(0, 5)))
        self.height_entry = toga.TextInput(style=Pack(flex=1))

        self.resize_button = toga.Button("Resize Image", on_press=self.resize_image, style=Pack(padding=(0, 5)))

        self.image_view = toga.ImageView(style=Pack(width=500, height=500))

        self.copyright_label = toga.Label("© 2024 Łukasz Kubieniec. All rights reserved.", style=Pack(padding=(0, 5)))

        self.github_link = toga.Button("GitHub: facior", on_press=self.open_github, style=Pack(padding=(0, 5)))

        box = toga.Box(
            children=[
                self.label,
                self.open_button,
                self.width_label,
                self.width_entry,
                self.height_label,
                self.height_entry,
                self.resize_button,
                self.image_view,
                self.copyright_label,
                self.github_link
            ],
            style=Pack(direction=COLUMN, padding=10)
        )

        self.main_window.content = box

    async def open_image(self, widget):
        self.file_path = await self.main_window.open_file_dialog('Select an image to resize', file_types=['jpg', 'jpeg', 'png', 'bmp', 'gif'])
        if self.file_path:
            self.image = Image.open(self.file_path)
            self.display_image(self.image)

    def display_image(self, img):
        img.thumbnail((500, 500))
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_path = temp_file.name
            img.save(temp_path, format='PNG')
        self.image_view.image = toga.Image(temp_path)

    async def resize_image(self, widget):
        if self.image is None:
            self.main_window.info_dialog("Error", "No image selected!")
            return

        try:
            width = int(self.width_entry.value)
            height = int(self.height_entry.value)
        except ValueError:
            self.main_window.info_dialog("Error", "Invalid width or height!")
            return

        resized_image = self.image.resize((width, height), Image.LANCZOS)
        save_path = await self.main_window.save_file_dialog('Save resized image', suggested_filename='resized_image.jpg', file_types=['jpg', 'jpeg', 'png', 'bmp', 'gif'])
        if save_path:
            file_format = save_path.suffix[1:].upper()
            if file_format == 'JPG':
                file_format = 'JPEG'
            if file_format == 'JPEG' and resized_image.mode == 'RGBA':
                resized_image = resized_image.convert('RGB')
            resized_image.save(save_path, format=file_format)
            self.main_window.info_dialog("Success", "Image resized and saved successfully!")
            self.display_image(resized_image)

    def set_logo(self, logo_path):
        self.icon = toga.Icon(logo_path)
        self.main_window.icon = toga.Icon(logo_path)

    def open_github(self, widget):
        webbrowser.open("https://github.com/facior")

def main():
    return ImageResizerApp("Image Resizer", app_id="com.example.imageresizer", icon="logo.png")

if __name__ == '__main__':
    main().main_loop()
