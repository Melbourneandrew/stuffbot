// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

import { createClient } from "jsr:@supabase/supabase-js@2"
import OpenAI from "npm:openai"
import { zodResponseFormat } from "npm:openai/helpers/zod"
import { z } from "npm:zod"

console.log("Hello from Functions!")

// Prompts and descriptions for OpenAI analysis
const LOCATION_PROMPT = "Looking at this room, describe where the highlighted item is positioned. Reference visible landmarks, furniture, or other objects to explain its location."
const LOCATION_DESCRIPTION = "A clear description (20-30 words) of the item's position relative to visible elements in the room (e.g., 'On the wooden shelf next to the window', 'Under the desk near the blue chair'). Start with 'This item is located' and then describe the location."

const ITEM_PROMPT = "What type of item is this and what would be its current resale value? If the image is too blurry, dark, or unclear to make a reasonable identification, respond with 'unknown' as the class and 0 as the price. Otherwise, provide a human-friendly, searchable name including the brand name if visible (e.g., 'Sony 55-inch TV', 'Nike running shoes', 'IKEA BILLY bookshelf'). Then estimate a conservative resale price in USD. Only classify as 'unknown' if you truly cannot make a reasonable guess about what the item is."
const ITEM_CLASS_DESCRIPTION = "A human-friendly, searchable name including the brand name if visible (e.g., 'Sony 55-inch TV', 'Nike running shoes', 'IKEA BILLY bookshelf'). Use 'unknown' only if the image is too unclear to make any reasonable identification"
const ITEM_PRICE_DESCRIPTION = "Estimated current resale value in USD (just the number, no currency symbol). Use 0 if the item is classified as unknown. Otherwise, estimate conservatively"

// Define types for the webhook payload
type TableRecord<T> = {
  id: string
  created_at: string
  class: string
  approximate_price: number
  location_description: string
  full_image_id: string
  partial_image_id: string
}

type WebhookPayload = {
  type: 'INSERT' | 'UPDATE' | 'DELETE'
  table: string
  schema: string
  record: TableRecord<any> | null
  old_record: TableRecord<any> | null
}

// Define Zod schemas for OpenAI responses
const LocationAnalysis = z.object({
  location_description: z.string().describe(LOCATION_DESCRIPTION),
})

const ItemAnalysis = z.object({
  class: z.string().describe(ITEM_CLASS_DESCRIPTION),
  approximate_price: z.number().describe(ITEM_PRICE_DESCRIPTION),
})

// Initialize clients
const openai = new OpenAI({
  apiKey: Deno.env.get('OPENAI_API_KEY') ?? '',
})
const supabase = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_ANON_KEY') ?? ''
)

Deno.serve(async (req) => {
  try {
    console.log('=== Starting request processing ===')
    const payload = await req.json() as WebhookPayload
    console.log('Received payload:', {
      type: payload.type,
      record_id: payload?.record?.id,
      current_class: payload?.record?.class
    })
    
    // Only process INSERT events
    if (payload.type !== 'INSERT' || !payload.record) {
      console.log('Skipping non-INSERT event or empty record')
      return new Response('Skipping non-INSERT event', { status: 200 })
    }

    // Check if we're in a potential loop
    if (payload.record.class !== 'unknown') {
      console.log('Skipping classification - class is already set:', payload.record.class)
      return new Response('Skipping - class already set', { status: 200 })
    }

    // Get last 10 unique classifications BEFORE processing the image
    const { data: recentClassifications, error: queryError } = await supabase
      .from('stuff')
      .select('class')
      .neq('class', 'unknown')
      .order('created_at', { ascending: false })
      .limit(50)  // Fetch more to account for duplicates

    if (queryError) throw queryError

    // Filter out duplicates and get first 10
    const uniqueClasses = [...new Set(recentClassifications.map(item => item.class))].slice(0, 10)
    console.log('Recent unique classifications:', uniqueClasses)

    const itemPromptWithClassifications = `${ITEM_PROMPT} Here are recently classified items - if the image matches any of these, respond with 'unknown': ${uniqueClasses.join(', ')}`

    // Download both images concurrently
    console.log('Downloading images...')
    const [fullImageData, partialImageData] = await Promise.all([
      supabase.storage.from('stuff_images_bucket').download(payload.record.full_image_id),
      supabase.storage.from('stuff_images_bucket').download(payload.record.partial_image_id)
    ])

    if (!fullImageData.data || !partialImageData.data) {
      throw new Error('Failed to download one or both images')
    }

    // Convert both images to base64
    const fullImageBase64 = btoa(
      new Uint8Array(await fullImageData.data.arrayBuffer())
        .reduce((data, byte) => data + String.fromCharCode(byte), '')
    )
    const partialImageBase64 = btoa(
      new Uint8Array(await partialImageData.data.arrayBuffer())
        .reduce((data, byte) => data + String.fromCharCode(byte), '')
    )

    // Process both analyses concurrently
    const [locationCompletion, itemCompletion] = await Promise.all([
      openai.beta.chat.completions.parse({
        model: "gpt-4o-mini",
        messages: [
          { 
            role: "user", 
            content: [
              { type: "text", text: LOCATION_PROMPT },
              { 
                type: "image_url", 
                image_url: { url: `data:image/jpeg;base64,${fullImageBase64}` }
              }
            ]
          }
        ],
        response_format: zodResponseFormat(LocationAnalysis, "location"),
      }),
      openai.beta.chat.completions.parse({
        model: "gpt-4o-mini",
        messages: [
          { 
            role: "user", 
            content: [
              { type: "text", text: itemPromptWithClassifications },
              { 
                type: "image_url", 
                image_url: { url: `data:image/jpeg;base64,${partialImageBase64}` }
              }
            ]
          }
        ],
        response_format: zodResponseFormat(ItemAnalysis, "item"),
      })
    ])

    // Clear image data
    fullImageData.data = null
    partialImageData.data = null

    console.log('Images processed successfully')

    console.log('Updating database with results:', {
      class: itemCompletion.choices[0].message.parsed.class,
      approximate_price: itemCompletion.choices[0].message.parsed.approximate_price,
      location_description: locationCompletion.choices[0].message.parsed.location_description,
    })

    const { error } = await supabase
      .from('stuff')
      .update({
        class: itemCompletion.choices[0].message.parsed.class,
        approximate_price: itemCompletion.choices[0].message.parsed.approximate_price,
        location_description: locationCompletion.choices[0].message.parsed.location_description,
      })
      .eq('id', payload.record.id)

    if (error) throw error

    console.log('=== Request completed successfully ===')
    return new Response('Analysis complete', { status: 200 })
  } catch (error) {
    console.error('Error:', error)
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}, {
  onError: (error) => {
    console.error('Fatal error:', error)
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  },
  // Set timeout to 60 seconds (default is 30 seconds)
  timeout: 60000
})

/* To invoke locally:

  1. Run `supabase start` (see: https://supabase.com/docs/reference/cli/supabase-start)
  2. Make an HTTP request:

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/classify_image' \
    --header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0' \
    --header 'Content-Type: application/json' \
    --data '{"name":"Functions"}'

*/
