export default async function handler(req, res) {
  if (req.method === "POST") {
    const body = req.body;

    if (body.message) {
      const chatId = body.message.chat.id;
      const text = body.message.text || "";

      await fetch(`https://api.telegram.org/bot${process.env.BOT_TOKEN}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          text: `You said: ${text}`,
        }),
      });
    }

    res.status(200).send("ok");
  } else {
    res.status(200).send("Webhook active");
  }
}
