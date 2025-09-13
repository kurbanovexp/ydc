import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk

# Совместимость Pillow
if hasattr(Image, 'Resampling'):
    RESAMPLE = Image.Resampling.LANCZOS
else:
    RESAMPLE = Image.ANTIALIAS


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("YOLO Dataset Creator")

        # Иконка окна
        try:
            self.root.iconphoto(False, tk.PhotoImage(file="icon.png"))
        except Exception:
            pass

        self.img = None
        self.tk_img = None
        self.image_list = []
        self.image_index = -1
        self.bboxes = {}
        self.classes = []
        self.current_class = None
        self.start_x = self.start_y = None
        self.selected_bbox = None  # индекс выбранного bbox

        # Верхнее меню
        frame_top = tk.Frame(root)
        frame_top.pack(fill=tk.X)

        tk.Button(frame_top, text="Открыть папку", command=self.open_folder).pack(side=tk.LEFT)
        tk.Button(frame_top, text="Сохранить", command=self.save_annotations).pack(side=tk.LEFT)
        tk.Button(frame_top, text="Экспортировать", command=self.export_dataset).pack(side=tk.LEFT)

        # Холст
        self.canvas = tk.Canvas(root, bg="gray", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # Нижняя панель
        frame_bottom = tk.Frame(root)
        frame_bottom.pack(fill=tk.X)

        tk.Button(frame_bottom, text="Предыдущее", command=self.prev_image).pack(side=tk.LEFT)
        tk.Button(frame_bottom, text="Следующее", command=self.next_image).pack(side=tk.LEFT)

        tk.Button(frame_bottom, text="Добавить класс", command=self.add_class).pack(side=tk.LEFT)
        tk.Button(frame_bottom, text="Удалить класс", command=self.delete_class).pack(side=tk.LEFT)
        self.class_listbox = tk.Listbox(frame_bottom)
        self.class_listbox.pack(side=tk.LEFT)
        self.class_listbox.bind("<<ListboxSelect>>", self.select_class)

        tk.Button(frame_bottom, text="Удалить выделение", command=self.delete_selected_bbox).pack(side=tk.LEFT)

        self.split_var = tk.DoubleVar(value=0.8)
        tk.Label(frame_bottom, text="Train Split:").pack(side=tk.LEFT)
        tk.Entry(frame_bottom, textvariable=self.split_var, width=5).pack(side=tk.LEFT)

        # Горячие клавиши
        self.root.bind("<Control-o>", lambda e: self.open_folder())
        self.root.bind("<Control-s>", lambda e: self.save_annotations())
        self.root.bind("<Control-e>", lambda e: self.export_dataset())
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Control-n>", lambda e: self.add_class())
        self.root.bind("<Control-d>", lambda e: self.delete_class())
        self.root.bind("<Delete>", lambda e: self.delete_selected_bbox())

    def open_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.image_list = [os.path.join(folder, f) for f in os.listdir(folder)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        self.image_list.sort()
        self.image_index = 0
        self.load_image()

    def load_image(self):
        if self.image_index < 0 or self.image_index >= len(self.image_list):
            return
        path = self.image_list[self.image_index]
        self.img = Image.open(path)
        w, h = self.img.size
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        scale = min(cw / w, ch / h)
        display_size = (int(w * scale), int(h * scale))
        resized = self.img.resize(display_size, RESAMPLE)
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self.tk_img)
        self.draw_bboxes()

    def on_mouse_down(self, event):
        if not self.current_class:
            messagebox.showerror("Ошибка", "Сначала выберите класс")
            return
        self.start_x, self.start_y = event.x, event.y
        self.selected_bbox = None

    def on_mouse_drag(self, event):
        if self.start_x and self.start_y:
            self.canvas.delete("preview")
            self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red", tags="preview")

    def on_mouse_up(self, event):
        if self.start_x and self.start_y:
            x1, y1, x2, y2 = self.start_x, self.start_y, event.x, event.y
            x1, x2 = sorted((x1, x2))
            y1, y2 = sorted((y1, y2))
            bbox = (x1, y1, x2, y2, self.current_class)
            self.bboxes.setdefault(self.image_list[self.image_index], []).append(bbox)
            self.start_x = self.start_y = None
            self.canvas.delete("preview")
            self.draw_bboxes()

    def on_right_click(self, event):
        path = self.image_list[self.image_index]
        if path not in self.bboxes:
            return
        for i, bbox in enumerate(self.bboxes[path]):
            x1, y1, x2, y2, cls = bbox
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.selected_bbox = i
                self.draw_bboxes()
                return

    def draw_bboxes(self):
        path = self.image_list[self.image_index]
        if path not in self.bboxes:
            return
        for i, bbox in enumerate(self.bboxes[path]):
            x1, y1, x2, y2, cls = bbox
            color = "red" if i != self.selected_bbox else "lime"
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
            self.canvas.create_text(x1 + 5, y1 + 5, text=cls, anchor="nw", fill="yellow")

    def prev_image(self):
        self.image_index -= 1
        if self.image_index < 0:
            self.image_index = 0
        self.load_image()

    def next_image(self):
        self.image_index += 1
        if self.image_index >= len(self.image_list):
            self.image_index = len(self.image_list) - 1
        self.load_image()

    def add_class(self):
        cls = simpledialog.askstring("Добавить класс", "Введите имя класса:")
        if cls and cls not in self.classes:
            self.classes.append(cls)
            self.class_listbox.insert(tk.END, cls)

    def delete_class(self):
        selection = self.class_listbox.curselection()
        if not selection:
            return
        cls = self.class_listbox.get(selection[0])
        self.classes.remove(cls)
        self.class_listbox.delete(selection[0])
        for path in self.bboxes:
            self.bboxes[path] = [bbox for bbox in self.bboxes[path] if bbox[4] != cls]
        if self.current_class == cls:
            self.current_class = None
        self.draw_bboxes()

    def select_class(self, event):
        selection = self.class_listbox.curselection()
        if selection:
            self.current_class = self.class_listbox.get(selection[0])

    def delete_selected_bbox(self):
        path = self.image_list[self.image_index]
        if path in self.bboxes and self.selected_bbox is not None:
            del self.bboxes[path][self.selected_bbox]
            self.selected_bbox = None
            self.draw_bboxes()

    def save_annotations(self):
        folder = filedialog.askdirectory(title="Папка для аннотаций")
        if not folder:
            return
        for img_path, boxes in self.bboxes.items():
            base = os.path.splitext(os.path.basename(img_path))[0]
            label_path = os.path.join(folder, base + ".txt")
            with open(label_path, "w") as f:
                for x1, y1, x2, y2, cls in boxes:
                    cls_id = self.classes.index(cls)
                    f.write(f"{cls_id} {x1} {y1} {x2} {y2}\n")
        with open(os.path.join(folder, "classes.txt"), "w") as f:
            for cls in self.classes:
                f.write(cls + "\n")
        messagebox.showinfo("Сохранено", "Аннотации сохранены!")

    def export_dataset(self):
        folder = filedialog.askdirectory(title="Папка для экспорта")
        if not folder:
            return
        train_split = self.split_var.get()
        os.makedirs(os.path.join(folder, "images/train"), exist_ok=True)
        os.makedirs(os.path.join(folder, "images/val"), exist_ok=True)
        os.makedirs(os.path.join(folder, "labels/train"), exist_ok=True)
        os.makedirs(os.path.join(folder, "labels/val"), exist_ok=True)
        for img_path in self.image_list:
            base = os.path.basename(img_path)
            subset = "train" if random.random() < train_split else "val"
            img_target = os.path.join(folder, f"images/{subset}", base)
            os.system(f"cp '{img_path}' '{img_target}'")
            if img_path in self.bboxes:
                label_target = os.path.join(folder, f"labels/{subset}", os.path.splitext(base)[0] + ".txt")
                with open(label_target, "w") as f:
                    for x1, y1, x2, y2, cls in self.bboxes[img_path]:
                        cls_id = self.classes.index(cls)
                        f.write(f"{cls_id} {x1} {y1} {x2} {y2}\n")
        with open(os.path.join(folder, "classes.txt"), "w") as f:
            for cls in self.classes:
                f.write(cls + "\n")
        messagebox.showinfo("Экспорт завершен", "Dataset готов!")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
