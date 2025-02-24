'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@supabase/supabase-js'

const POLLING_INTERVAL_MS = 1000 // 3 seconds

// Initialize Supabase client
const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

interface StuffItem {
    id: string
    class: string
    approximate_price: number
    location_description: string
    full_image_id: string
    partial_image_id: string
    created_at: string
}

export default function Home() {
    const [stuffItems, setStuffItems] = useState<StuffItem[]>([])
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedItem, setSelectedItem] = useState<StuffItem | null>(null)

    useEffect(() => {
        // Initial fetch
        fetchStuff()

        // Set up polling interval
        const pollInterval = setInterval(fetchStuff, POLLING_INTERVAL_MS)

        // Cleanup interval on component unmount
        return () => clearInterval(pollInterval)
    }, [])

    async function fetchStuff() {
        const { data, error } = await supabase
            .from('stuff')
            .select('*')
            .order('created_at', { ascending: false })

        if (error) {
            console.error('Error fetching stuff:', error)
            return
        }

        setStuffItems(data || [])
    }

    const filteredItems = stuffItems.filter(item =>
        item.class.toLowerCase() !== 'unknown' && (
            item.class.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.location_description.toLowerCase().includes(searchTerm.toLowerCase())
        )
    )

    return (
        <main className="container mx-auto px-4 py-8">
            <h1 className="text-5xl font-bold text-center mb-2">StuffBot 🤖</h1>
            <p className="text-center text-gray-500 mb-8">Finding your lost treasures, one pixel at a time. Built with <a href="https://bracket.bot" className="text-primary hover:underline">BracketBot</a></p>

            <div className="form-control w-full mx-auto mb-8">
                <input
                    type="text"
                    placeholder="Search stuff..."
                    className="input input-bordered w-full rounded-md"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            <div className="flex flex-col gap-6">
                {filteredItems.map((item) => (
                    <div
                        key={item.id}
                        className="card card-side bg-base-100 shadow-xl hover:shadow-2xl hover:scale-[1.02] transition-all duration-300 cursor-pointer border border-base-300"
                        onClick={() => setSelectedItem(item)}
                    >
                        {item.partial_image_id && (
                            <figure className="w-[250px] min-w-[250px] h-[250px] flex items-center justify-center p-6 bg-base-200">
                                <img
                                    src={`${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/stuff_images_bucket/${item.partial_image_id}`}
                                    alt={item.class}
                                    className="max-w-full max-h-full object-contain m-auto"
                                />
                            </figure>
                        )}
                        <div className="card-body">
                            <h2 className="card-title text-2xl">{item.class}</h2>
                            <p>{item.location_description}</p>
                            <div className="flex justify-between items-center">
                                <div>
                                    <p className="text-primary font-semibold">
                                        ${item.approximate_price?.toLocaleString(undefined, {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        })}
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        Last Seen: {new Date(item.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <button className="btn btn-primary text-white">Find</button>
                                    {/* <button className="btn btn-primary text-white">Sell $</button> */}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Modal */}
            {selectedItem && (
                <dialog className="modal modal-open">
                    <div className="modal-box max-w-3xl max-h-[90vh]">
                        <h3 className="font-bold text-lg mb-4">{selectedItem.class}</h3>
                        <div className="flex flex-col gap-4">
                            <div className="grid grid-cols-2 gap-4">
                                {selectedItem.partial_image_id && (
                                    <div className="w-full">
                                        <p className="font-semibold mb-2">Item Image:</p>
                                        <img
                                            src={`${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/stuff_images_bucket/${selectedItem.partial_image_id}`}
                                            alt={`${selectedItem.class}`}
                                            className="w-full h-auto max-h-[400px] object-contain rounded-lg"
                                        />
                                    </div>
                                )}
                                {selectedItem.full_image_id && (
                                    <div className="w-full">
                                        <p className="font-semibold mb-2">Last Seen Location:</p>
                                        <img
                                            src={`${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/stuff_images_bucket/${selectedItem.full_image_id}`}
                                            alt={`${selectedItem.class} location`}
                                            className="w-full h-auto max-h-[400px] object-contain rounded-lg"
                                        />
                                    </div>
                                )}
                            </div>
                            <div>
                                <p className="font-semibold">Location Description:</p>
                                <p>{selectedItem.location_description}</p>
                            </div>
                            <div>
                                <p className="font-semibold">Approximate Value:</p>
                                <p className="text-primary font-semibold">
                                    ${selectedItem.approximate_price?.toLocaleString(undefined, {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    })}
                                </p>
                            </div>
                            <p className="text-sm text-gray-500">
                                Last Seen: {new Date(selectedItem.created_at).toLocaleDateString()}
                            </p>
                        </div>
                        <div className="modal-action">
                            <button
                                className="btn"
                                onClick={() => setSelectedItem(null)}
                            >
                                Close
                            </button>
                        </div>
                    </div>
                    <form method="dialog" className="modal-backdrop">
                        <button onClick={() => setSelectedItem(null)}>close</button>
                    </form>
                </dialog>
            )}
        </main>
    )
}
