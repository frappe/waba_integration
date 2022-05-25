// Copyright (c) 2022, Hussain Nagaria and contributors
// For license information, please see license.txt

frappe.ui.form.on("WABA WhatsApp Message", {
  refresh: function (frm) {
    if (!frm.doc.id) {
      const btn = frm.add_custom_button("Send Message", () => {
        frm
          .call({
            doc: frm.doc,
            method: "send",
            btn,
          })
          .then((m) => frm.refresh());
      });
    }

    if (
      ["Image", "Video", "Audio", "Document"].includes(frm.doc.message_type) &&
      !frm.doc.media_file
    ) {
      const btn = frm.add_custom_button("Download Attachment File", () => {
        frm
          .call({
            doc: frm.doc,
            method: "download_media",
            btn,
          })
          .then((data) => {
            const file = data.message;
            frm.refresh();
            frappe.msgprint({
              title: "Attachment downloaded successfully.",
              message: `Attachment File: <a href="${file.file_url}" target="_blank">${file.file_name}</a>`,
              indicator: "green",
            });
          });
      });
    }

    if (frm.doc.preview_html) {
      let wrapper = frm.get_field("preview_html_rendered").$wrapper;
      wrapper.html(frm.doc.preview_html);
    }
  },
});
