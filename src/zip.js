/**
 * Minimal in-browser ZIP archive builder (Store mode / uncompressed).
 * Designed for bundling pre-compressed assets (PNG, WebP).
 *
 * Implements standard PKZIP specification (APPNOTE.TXT):
 * - CRC-32 table computation (polynomial 0xEDB88320)
 * - Local File Header (0x04034b50 / "PK\x03\x04")
 * - Central Directory Header (0x02014b50 / "PK\x01\x02")
 * - End of Central Directory Record (0x06054b50 / "PK\x05\x06")
 */
(() => {
  // Precompute CRC-32 lookup table
  const CRC_TABLE = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    }
    CRC_TABLE[n] = c >>> 0;
  }

  function computeCrc32(bytes) {
    let crc = ~0;
    for (let i = 0; i < bytes.length; i++) {
      crc = CRC_TABLE[(crc ^ bytes[i]) & 255] ^ (crc >>> 8);
    }
    return (~crc) >>> 0;
  }

  window.makeZip = async function makeZip(files) {
    const encoder = new TextEncoder();
    const fileParts = [];
    const centralDirectoryEntries = [];
    let offset = 0;

    const now = new Date();
    const dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
    const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);

    for (const file of files) {
      const data = new Uint8Array(await file.blob.arrayBuffer());
      const encodedName = encoder.encode(file.name);
      const crc = computeCrc32(data);

      // 1. Local file header (30 bytes)
      const localHeader = new DataView(new ArrayBuffer(30));
      localHeader.setUint32(0, 0x04034b50, true);          // Local file header signature (PK\x03\x04)
      localHeader.setUint16(4, 20, true);                  // Version needed to extract (2.0)
      localHeader.setUint16(6, 0x0800, true);               // General purpose bit flag (UTF-8)
      localHeader.setUint16(8, 0, true);                    // Compression method (0 = store)
      localHeader.setUint16(10, dosTime, true);             // File modification time
      localHeader.setUint16(12, dosDate, true);             // File modification date
      localHeader.setUint32(14, crc, true);                 // CRC-32 checksum
      localHeader.setUint32(18, data.length, true);         // Compressed size
      localHeader.setUint32(22, data.length, true);         // Uncompressed size
      localHeader.setUint16(26, encodedName.length, true);  // File name length
      localHeader.setUint16(28, 0, true);                   // Extra field length

      fileParts.push(localHeader, encodedName, data);

      // 2. Central directory record (46 bytes)
      const cdEntry = new DataView(new ArrayBuffer(46));
      cdEntry.setUint32(0, 0x02014b50, true);               // Central directory signature (PK\x01\x02)
      cdEntry.setUint16(4, 20, true);                       // Version made by (2.0)
      cdEntry.setUint16(6, 20, true);                       // Version needed to extract (2.0)
      cdEntry.setUint16(8, 0x0800, true);                    // General purpose bit flag (UTF-8)
      cdEntry.setUint16(10, 0, true);                       // Compression method (0 = store)
      cdEntry.setUint16(12, dosTime, true);                  // File modification time
      cdEntry.setUint16(14, dosDate, true);                  // File modification date
      cdEntry.setUint32(16, crc, true);                      // CRC-32
      cdEntry.setUint32(20, data.length, true);              // Compressed size
      cdEntry.setUint32(24, data.length, true);              // Uncompressed size
      cdEntry.setUint16(28, encodedName.length, true);        // File name length
      cdEntry.setUint16(30, 0, true);                        // Extra field length
      cdEntry.setUint16(32, 0, true);                        // File comment length
      cdEntry.setUint16(34, 0, true);                        // Disk number start
      cdEntry.setUint16(36, 0, true);                        // Internal file attributes
      cdEntry.setUint32(38, 0, true);                        // External file attributes
      cdEntry.setUint32(42, offset, true);                   // Relative offset of local header

      centralDirectoryEntries.push(cdEntry, encodedName);
      offset += 30 + encodedName.length + data.length;
    }

    // 3. End of central directory record (22 bytes)
    const cdSize = centralDirectoryEntries.reduce((sum, item) => sum + item.byteLength, 0);
    const eocd = new DataView(new ArrayBuffer(22));
    eocd.setUint32(0, 0x06054b50, true);                   // End of central directory signature (PK\x05\x06)
    eocd.setUint16(4, 0, true);                            // Number of this disk
    eocd.setUint16(6, 0, true);                            // Disk where central directory starts
    eocd.setUint16(8, files.length, true);                 // Number of central directory records on this disk
    eocd.setUint16(10, files.length, true);                // Total number of central directory records
    eocd.setUint32(12, cdSize, true);                      // Size of central directory
    eocd.setUint32(16, offset, true);                      // Offset of start of central directory
    eocd.setUint16(20, 0, true);                           // Comment length

    return new Blob([...fileParts, ...centralDirectoryEntries, eocd], {
      type: 'application/zip'
    });
  };
})();
