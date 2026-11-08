import { tool } from "@opencode-ai/plugin"

/**
 * Custom Tool для чтения страницы Confluence напрямую через REST API.
 *
 * Требует переменные окружения:
 *   CONFLUENCE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN
 *
 * Только чтение: принцип Least Privilege, никаких операций изменения.
 */
export default tool({
    description: "Получить страницу Confluence по pageId (только чтение)",

    args: {
        pageId: tool.schema.string()
    },

    async execute(args) {
        const baseUrl = process.env.CONFLUENCE_URL
        const email = process.env.CONFLUENCE_EMAIL
        const token = process.env.CONFLUENCE_API_TOKEN

        if (!baseUrl || !email || !token) {
            throw new Error("Не заданы переменные окружения Confluence")
        }

        const auth = Buffer.from(`${email}:${token}`).toString("base64")
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 30000)

        try {
            const response = await fetch(
                `${baseUrl}/wiki/api/v2/pages/${args.pageId}?body-format=storage`,
                {
                    method: "GET",
                    headers: {
                        Authorization: `Basic ${auth}`,
                        Accept: "application/json"
                    },
                    signal: controller.signal
                }
            )

            if (response.status === 429) {
                throw new Error("Confluence rate limit: повторите запрос позже")
            }
            if (!response.ok) {
                throw new Error(
                    `Confluence API error: ${response.status} ${response.statusText}`
                )
            }

            const data = await response.json()
            return JSON.stringify(data)
        } finally {
            clearTimeout(timeout)
        }
    }
})
